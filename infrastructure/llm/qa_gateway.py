from ...qa.agent import QAAgent


class QAGatewayAdapter:
    def __init__(self):
        self.qa = QAAgent()

    def validate_email(self, payload: dict) -> dict:
        return self.qa.validate_email(payload)
