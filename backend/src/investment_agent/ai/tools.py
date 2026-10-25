"""Read-only tools over one analysis payload. No shell, files, HTTP, ledger, approval or messaging."""

from .payloads import AiPayload


class ToolBox:
    def __init__(self, payload: AiPayload):
        self._entities = {e.ticker: e for e in payload.entities}
        self._evidence = {e.evidence_id: e for e in payload.evidence}
        self._portfolio = payload.portfolio
        self._tools = {
            "get_entity_facts": (self._entity, {"ticker": "string"}, "Tỷ lệ tài chính và vị trí vùng giá của một mã trong gói phân tích."),
            "get_evidence": (self._doc, {"evidence_id": "string"}, "Một trích đoạn bằng chứng công khai theo mã bằng chứng."),
            "get_portfolio_weights": (self._weights, {}, "Tỷ trọng danh mục theo vốn có thể đầu tư, nhóm rủi ro và các cờ giới hạn."),
        }

    def _entity(self, ticker):
        return self._entities[ticker].model_dump(mode="json")

    def _doc(self, evidence_id):
        return self._evidence[evidence_id].model_dump(mode="json")

    def _weights(self):
        return self._portfolio.model_dump(mode="json")

    def allowed(self, name: str) -> bool:
        return name in self._tools

    def call(self, name: str, arguments: dict) -> dict:
        fn, params, _ = self._tools[name]
        if set(arguments) != set(params) or any(not isinstance(v, str) for v in arguments.values()):
            raise KeyError("bad_arguments")
        return fn(**arguments)

    def definitions_names(self) -> list[str]:
        return list(self._tools)

    def definitions(self) -> list[dict]:
        return [{"type": "function", "function": {"name": name, "description": desc,
                 "parameters": {"type": "object", "properties": {p: {"type": t} for p, t in params.items()},
                                "required": list(params), "additionalProperties": False}}}
                for name, (_, params, desc) in self._tools.items()]
