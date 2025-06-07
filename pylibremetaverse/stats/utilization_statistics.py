# Stub for UtilizationStatistics

class UtilizationStatistics:
    def __init__(self):
        """
        Initializes statistics collection.
        """
        # Example stats - these would be updated by various parts of the client
        self.bytes_in: int = 0
        self.bytes_out: int = 0
        self.packets_in: int = 0
        self.packets_out: int = 0
        # Add other relevant stats as needed
        pass

    def sent_bytes(self, num_bytes: int, num_packets: int):
        self.bytes_out += num_bytes
        self.packets_out += num_packets

    def received_bytes(self, num_bytes: int, num_packets: int):
        self.bytes_in += num_bytes
        self.packets_in += num_packets

    def clear(self):
        self.bytes_in = 0
        self.bytes_out = 0
        self.packets_in = 0
        self.packets_out = 0

    def __str__(self) -> str:
        return (f"Bytes In: {self.bytes_in}, Bytes Out: {self.bytes_out}, "
                f"Packets In: {self.packets_in}, Packets Out: {self.packets_out}")
