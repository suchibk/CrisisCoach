# Streamlit views

`streamlit_app.py` selects Live incident/Practice and Incident/Evidence pack/Profile. `incident.py` shows the current instruction and gates; `collection.py` adapts capture/context events; `report.py` reviews originals/gaps and exports; `profile.py` manages optional preparation; `practice.py` provides suggestions and backend-derived traces; `presentation.py` computes display data; `appearance.py` contains local responsive styles.

All incident writes go through WorkflowEngine. Profile snapshots attach only to new incidents and do not silently select knowledge context. PracticeRuntime supplies separate temporary storage, synthetic profiles and images, fake review, and a manually advanced clock. Switching back to a live incident reopens it with fresh safety checks. Practice reset/exit disposes its temporary directory. Real voice controls are only rendered in Live incident mode.

Streamlit AppTest tests cover controls, themes, capture, exports, reset, profile snapshots, and mode isolation. The opt-in Playwright suite covers actual browser upload/download, layout, sidebar controls, and keyboard focus. Native microphone and live provider compatibility need separate device testing.
