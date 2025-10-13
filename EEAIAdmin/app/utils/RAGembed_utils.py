# app/utils/embed_utils.py
import openai


def get_embedding(text: str):
    response = openai.Embedding.create(
        input=[text],
        engine="text-embedding-ada-002"  # ✅ now uses env variable
    )
    return response["data"][0]["embedding"]

def format_record(record: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in record.items() if v and v != 'NULL')


if __name__ == "__main__":
    from app.utils import RAGoracle_utils
    import json
    from pathlib import Path

    records = RAGoracle_utils.fetch_oracle_data()
    docs = []
    for i, rec in enumerate(records):
        text = format_record(rec)
        if text:
            emb = get_embedding(text)
            docs.append({"id": f"trx_{i}", "text": text, "embedding": emb})

    Path("app/utils/embedded_oracle_data.json").write_text(json.dumps(docs, indent=2))
    print(f"✅ Embedded {len(docs)} records and saved to embedded_oracle_data.json")
