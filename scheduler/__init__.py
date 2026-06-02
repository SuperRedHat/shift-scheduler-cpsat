"""CP-SAT multi-party meeting scheduler with an infeasibility explainer.

See model.Scheduler (build/solve/explain_infeasible), checker.violations (an
independent solution verifier), and scenarios for the demo data.
"""
from .model import Meeting, Participant, Scheduler, SolveResult
from .checker import violations

__all__ = ["Meeting", "Participant", "Scheduler", "SolveResult", "violations"]
__version__ = "1.0.0"
