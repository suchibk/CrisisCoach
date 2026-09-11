# Local danger policy, version 1

Implementation review: 2026-09-11. These bounded phrase rules are not clinical validation or a comprehensive threat classifier. Independent domain-expert review remains outstanding.

Current reports of directed shouting/threats stop collection. The response avoids instructions to enter a potentially unsafe vehicle. Emergency escalation is conditional on immediate danger. Fire/smoke/fuel-leak reports stop collection and direct the user away from the vehicle and traffic. Injury retains precedence. Paused conversations still enter the guard. An environmental stand-down needs an explicit away-from-danger statement followed by all safety gates; it never accepts medical clearance as environmental clearance.

Sources inspected 2026-09-11:
- US Fire Administration, Vehicle Fire Safety: https://www.usfa.fema.gov/prevention/vehicle-fires/ (leave the vehicle, stay away from traffic, do not return, call 911).
- National 911 Program, Calling 911: https://www.911.gov/calling-911/ (emergencies requiring immediate police/fire/ambulance assistance; follow dispatcher instructions).

Hypothetical prefixes and direct negation are covered by regression tests; quoted reports of current threats still stop collection. Language beyond the explicit patterns may be missed. The US emergency number follows the existing collision prototype; geographic emergency-number selection remains pending. No policy/liability conclusion follows from an apology. Neutral guidance preserves the original account and current task.
