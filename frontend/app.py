"""
Sahi Dawa: Frontend (Gradio, thin client over the real FastAPI backend)

No logic lives here: no matching, no pricing, no history storage, no fake
RAG. Every fact shown comes from API_URL. If the backend isn't running,
this app has nothing to show by design.
"""

import gradio as gr
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000"


def _get(path):
    try:
        resp = requests.get(f"{API_URL}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.ConnectionError:
        return None, f"Cannot reach backend at {API_URL}. Is `uvicorn app.main:app` running?"
    except requests.exceptions.HTTPError as e:
        return None, f"Backend error: {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"


def _post(path, payload):
    try:
        resp = requests.post(f"{API_URL}{path}", json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.ConnectionError:
        return None, f"Cannot reach backend at {API_URL}. Is `uvicorn app.main:app` running?"
    except requests.exceptions.HTTPError as e:
        return None, f"Backend error: {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"


def _flags_markdown(flags):
    if not flags:
        return "_No discussion flags in this patient's history._"
    return "\n\n".join(
        f"🚩 **{f['flag_type']}**: {f['message']}\n\n*{f['safety_note']}*" for f in flags
    )


def _record_markdown(record):
    if not record:
        return ""
    badge = "✅ VERIFIED" if record.get("data_status") == "VERIFIED" else "⚠️ DEMO / SYNTHETIC"
    price = f"PKR {record['price']}" if record.get("price") is not None else "Not available"
    return (
        f"### {record['brand_name']}\n"
        f"**Generic name:** {record['generic_name']}  \n"
        f"**Active ingredient:** {record['active_ingredient']}  \n"
        f"**Strength:** {record['strength']}  \n"
        f"**Dosage form:** {record['dosage_form']}  \n"
        f"**Pack size:** {record['pack_size']}  \n"
        f"**Manufacturer:** {record['manufacturer']}  \n"
        f"**Price:** {price}  \n"
        f"**Data status:** {badge}  \n"
        f"**Last verified:** {record.get('last_verified') or 'N/A'}  \n"
        f"**Source:** {record.get('drap_source_url') or 'N/A'}\n"
    )


def _alternatives_dataframe(alternatives):
    cols = ["brand_name", "strength", "dosage_form", "pack_size",
            "manufacturer", "price", "unit_price", "data_status"]
    if not alternatives:
        return pd.DataFrame(columns=cols)
    df = pd.DataFrame(alternatives)
    return df[[c for c in cols if c in df.columns]]


def _price_comparison_markdown(pc):
    if not pc:
        return ""
    lines = [f"**Current price:** {pc.get('current_price')} (pack: {pc.get('current_pack_size')})"]
    if pc.get("current_unit_price") is not None:
        lines.append(f"**Current unit price:** {pc['current_unit_price']} per {pc.get('current_pack_unit')}")
    if pc.get("lowest_pack_price") is not None:
        lines.append(
            f"**Lowest pack price:** {pc['lowest_pack_price']} "
            f"({pc.get('lowest_pack_price_medicine_id')}, pack: {pc.get('lowest_pack_price_pack_size')})"
        )
    if pc.get("comparison_basis") == "UNIT_PRICE" and pc.get("lowest_unit_price") is not None:
        lines.append(
            f"**Lowest unit price:** {pc['lowest_unit_price']} per {pc.get('lowest_unit_price_unit')} "
            f"({pc.get('lowest_unit_price_medicine_id')})"
        )
    else:
        lines.append("_Unit-price comparison not available for these pack sizes — showing total pack price only._")
    lines.append(f"\n> {pc.get('note', '')}")
    return "\n\n".join(lines)


def analyze_prescription(patient_id, diagnosis, medicine, dosage):
    if not patient_id or not diagnosis or not medicine:
        return "Please fill in patient ID, diagnosis and medicine name.", pd.DataFrame(), "", pd.DataFrame(), ""

    payload = {"patient_id": patient_id, "diagnosis": diagnosis, "medicine": medicine, "dosage": dosage or None}
    data, error = _post("/prescription", payload)
    if error:
        return error, pd.DataFrame(), "", pd.DataFrame(), ""

    status = data.get("status")
    if status == "NOT_FOUND":
        return f"⚠️ {data.get('message')}", pd.DataFrame(), "", pd.DataFrame(), ""
    if status == "AMBIGUOUS":
        return f"⚠️ {data.get('message')}", pd.DataFrame(data.get("candidates", [])), "", pd.DataFrame(), ""

    ai_note = (
        "\n\n---\n_AI-generated plain-language explanation is pending the RAG layer "
        "(in progress) all facts above come directly from the verified catalogue._"
    )
    return (
        _record_markdown(data.get("medicine")) + ai_note,
        pd.DataFrame(),
        _price_comparison_markdown(data.get("price_comparison")),
        _alternatives_dataframe(data.get("alternatives", [])),
        _flags_markdown(data.get("pattern_flags", [])),
    )


def fetch_history(patient_id):
    if not patient_id:
        return pd.DataFrame(), ""
    data, error = _get(f"/history/{patient_id}")
    if error:
        return pd.DataFrame(), error
    encounters = data.get("encounters", [])
    df = pd.DataFrame(encounters) if encounters else pd.DataFrame(
        columns=["encounter_id", "diagnosis", "medicine_id", "medicine_name",
                 "medicine_category", "dosage", "encounter_date"]
    )
    return df, _flags_markdown(data.get("pattern_flags", []))


def generate_summary(patient_id):
    """Assembled client-side from /history -- there is no dedicated /summary
    endpoint yet (PRD Section 15). Replace this with a real call once it
    exists. Nothing here is invented; it's the same data as the History tab,
    reframed as a report."""
    if not patient_id:
        return "", pd.DataFrame(), ""
    data, error = _get(f"/history/{patient_id}")
    if error:
        return error, pd.DataFrame(), ""
    encounters = data.get("encounters", [])
    note = (
        "**Sahi Dawa does not diagnose or prescribe.** This summary reflects your recorded "
        "prescription history and any discussion flags. Please discuss this report with your "
        "doctor or pharmacist.\n\n_(Assembled from stored history; a dedicated shareable-report "
        "endpoint is in progress.)_"
    )
    return note, pd.DataFrame(encounters), _flags_markdown(data.get("pattern_flags", []))


with gr.Blocks(title="Sahi Dawa") as demo:
    gr.Markdown("# 💊 Sahi Dawa: AI Prescription Transparency & Care Assistant")
    gr.Markdown("> **Core Principle:** We don't replace the doctor. We make the prescription transparent.")
    gr.Markdown(f"_Connected to backend at `{API_URL}` — make sure `uvicorn app.main:app` is running._")

    with gr.Tab("📋 Enter Prescription"):
        with gr.Row():
            p_id = gr.Textbox(label="Patient ID", value="P001")
            diag = gr.Textbox(label="Diagnosis", value="Bacterial infection")
            med = gr.Textbox(label="Medicine Name (brand or generic)")
            dos = gr.Textbox(label="Dosage / Strength (optional, e.g. 500mg)")
        btn = gr.Button("Analyze Prescription", variant="primary")
        record_out = gr.Markdown(label="Verified Medicine Record")
        candidates_out = gr.Dataframe(label="Multiple matches — specify strength/dosage")
        price_out = gr.Markdown(label="Price Comparison")
        alts_out = gr.Dataframe(label="Same-Medicine Alternatives")
        flags_out = gr.Markdown(label="Discussion Flags")
        btn.click(analyze_prescription, [p_id, diag, med, dos],
                  [record_out, candidates_out, price_out, alts_out, flags_out])

    with gr.Tab("📜 Patient History"):
        p_id_hist = gr.Textbox(label="Patient ID", value="P001")
        btn_hist = gr.Button("Fetch History")
        hist_table = gr.Dataframe(label="Encounters")
        hist_flags = gr.Markdown(label="Discussion Flags")
        btn_hist.click(fetch_history, [p_id_hist], [hist_table, hist_flags])

    with gr.Tab("📄 Health Summary"):
        gr.Markdown("_Assembled from stored history — will move to a dedicated backend endpoint once built._")
        p_id_sum = gr.Textbox(label="Patient ID", value="P001")
        btn_sum = gr.Button("Generate Summary")
        note_out = gr.Markdown()
        sum_table = gr.Dataframe()
        sum_flags = gr.Markdown()
        btn_sum.click(generate_summary, [p_id_sum], [note_out, sum_table, sum_flags])

if __name__ == "__main__":
    demo.launch()
