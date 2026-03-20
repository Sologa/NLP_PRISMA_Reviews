Return a corrected JSON object that fixes the validator failure exactly.

Rules:

- keep the same output schema
- do not add prose outside the JSON object
- keep score and recommendation aligned
- keep lists JSON-valid
- if evidence is insufficient, prefer `3` / `maybe` rather than inventing support
