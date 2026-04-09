class AppState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.lan_ip = "127.0.0.1"
        self.internal_ip = "127.0.0.1"
        self.local_port = 8556
        self.latest_code_b64 = ""
        self.latest_needs_stl = False
        self.injected_code_ia = ""
        self.vision_b64 = ""
        self.last_error_log = ""
        self.agentic_payload = None

        self.assembly_parts_state = [
            {"active": False, "file": "", "mat": "pla", "x": 0, "y": 0, "z": 0}
            for _ in range(10)
        ]
        self.pbr_state = {"mode": "single", "parts": []}

    def update_pbr_state(self):
        self.pbr_state["mode"] = "assembly"
        self.pbr_state["parts"] = [p for p in self.assembly_parts_state if p["active"]]

state = AppState()
