"""When a case folder has no machine-readable service file (no OpenAPI), the services are described in prose: a
contract document with example requests and answers. This step writes the OpenAPI file from that prose, so that the
reader and the compiler work from one typed interface. Nothing here knows a particular bank: the model is told to copy
paths, field names, types, envelopes and error codes exactly from the documents."""
import json
import os

from reader import llm

SYSTEM = """You turn a written service contract into an OpenAPI 3.0 JSON file. Reply with one JSON object only.

Rules:
- One path per service, exactly as the document writes it (full path under the base address; put the base address in
  servers[0].url). Method as documented.
- operationId: the service name with every character that is not a letter, digit or underscore replaced by an underscore
  (lowercase). Example: a service called 'a.b.c' gets operationId 'a_b_c'. The path keeps the document's exact spelling.
- Copy field names exactly. Use the documented JSON types (a value the document says may be sent as string OR number is
  type string). An identifier (customer number, card number, account number) is type string, never integer.
- If requests and answers use an envelope (for example a request {data: {...fields...}, call: {...metadata...}} and an
  answer {data: {...}, result: {...}}), describe the envelope literally: requestBody schema with properties 'data'
  (object with the service's fields and a 'required' list) and any metadata objects; for metadata fields that have a
  documented constant value, give them a 'default'. The 2xx response schema has 'data' (object with all documented fields,
  nested objects and arrays described with their properties) and 'result'.
- Describe every documented error (HTTP status, code, when it happens, which services) in the 'responses' of the
  operations it applies to, with the error body schema, and say in the operation 'description' what each error code means.
- Put business meaning that the document gives for fields into 'description' fields (short). Do not invent fields.
- Do not write a path for a token / login endpoint (the assistant never calls it); say in info.description how requests are
  authenticated.
- info.title and info.description: one line each."""


def looks_like_service_doc(path):
    return path.lower().endswith((".md", ".txt", ".markdown"))


def make_openapi(brief_files, out_path):
    docs = []
    for p in brief_files:
        if not looks_like_service_doc(p):
            continue
        t = open(p, encoding="utf-8", errors="replace").read()
        if any(w in t.lower() for w in ("endpoint", "request", "response", "`post`", "http", "base address", "base url")):
            docs.append((p, t))
    if not docs:
        raise SystemExit("no OpenAPI file and no document that describes the services")
    prompt = "Documents (use the ones that define the services; ignore the rest):\n\n" + "\n\n".join(
        "=== %s ===\n%s" % (os.path.basename(p), t) for p, t in docs)
    last = None
    for attempt in range(2):
        text = llm.call(SYSTEM, prompt, purpose="write OpenAPI from the service contract" + (" (retry)" if attempt else ""), max_tokens=32000)
        try:
            spec = llm.extract_json(text)
            if isinstance(spec, dict) and spec.get("paths"):
                json.dump(spec, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                return out_path
        except Exception as e:
            last = e
    raise SystemExit("could not write an OpenAPI file from the documents: %s" % last)
