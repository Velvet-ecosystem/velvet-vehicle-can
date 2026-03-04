from __future__ import annotations

import time
import logging

logger = logging.getLogger(__name__)
from velvet_vehicle_can.can_backend import PythonCanReader, SocketCanConfig
from velvet_vehicle_can.can_sniffer_service import CanSnifferService, SnifferConfig
from velvet_vehicle_can.qualification_gate import DriverState


def run_sniffer(channel: str = "can0") -> None:
    reader = PythonCanReader(SocketCanConfig(channel=channel, receive_timeout_s=0.0))
    sniffer = CanSnifferService(
        read_frame=reader.read_frame,
        config=SnifferConfig(bus_name=channel),
    )

    # For now: assume driver present/attentive; other modules will update this in real system
    sniffer.set_driver_state(DriverState(driver_present=True, attentive=True))

    t0 = time.time()
    last_print = 0.0

    while True:
        st = sniffer.tick()

        now = time.time()
        if now - last_print > 1.0:
            last_print = now
            fp = st.fingerprint.digest() if st.fingerprint else "none"
            stage = st.qualification.allowed_stage.name if st.qualification else "none"
            logger.info(
                f"[sniffer] fp={fp} frames={len(sniffer.frames)} stage={stage}"
            )

        # Optional: periodic learning pass if you have labeled events coming in
        # if int(now - t0) % 5 == 0:
        #     sniffer.run_learning_pass(lookback_s=15.0)

        time.sleep(0.005)  # ~200 Hz loop


if __name__ == "__main__":
    run_sniffer("can0")
