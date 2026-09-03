import uuid
from app.repositories.attempt_repository import AttemptRepository

class ProblemNotFound(Exception): pass

class AttemptService:
    def __init__(self, attempts: AttemptRepository, problems): self.attempts, self.problems = attempts, problems
    def create(self, problem_id: str):
        if self.problems.get(problem_id) is None: raise ProblemNotFound
        return self.attempts.create(problem_id)
    def get(self, attempt_id: uuid.UUID): return self.attempts.get(attempt_id)
