from dataclasses import dataclass, field
from typing import List, Dict, Optional
import time

@dataclass
class MockFile:
    filename: str
    content: str
    language: str

@dataclass
class MockPR:
    id: int
    title: str
    files: List[MockFile]
    status: str = "OPEN" # OPEN, MERGED, CLOSED
    comments: List[str] = field(default_factory=list)
    checks: Dict[str, str] = field(default_factory=dict) # check_name -> status (PENDING, PASS, FAIL)

class MockGitHub:
    def __init__(self):
        self.prs: Dict[int, MockPR] = {}
        self.next_pr_id = 1

    def create_pr(self, title: str, files: List[MockFile]) -> MockPR:
        pr = MockPR(id=self.next_pr_id, title=title, files=files)
        self.prs[self.next_pr_id] = pr
        self.next_pr_id += 1
        return pr

    def get_pr(self, pr_id: int) -> Optional[MockPR]:
        return self.prs.get(pr_id)

    def add_comment(self, pr_id: int, comment: str):
        if pr_id in self.prs:
            self.prs[pr_id].comments.append(comment)

    def update_check_status(self, pr_id: int, check_name: str, status: str):
        if pr_id in self.prs:
            self.prs[pr_id].checks[check_name] = status

    def merge_pr(self, pr_id: int):
        if pr_id in self.prs:
            self.prs[pr_id].status = "MERGED"

    def update_file_content(self, pr_id: int, filename: str, new_content: str):
         if pr_id in self.prs:
            for file in self.prs[pr_id].files:
                if file.filename == filename:
                    file.content = new_content
                    return
