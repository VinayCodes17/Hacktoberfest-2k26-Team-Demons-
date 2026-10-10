from app.schemas import ErrorCluster, RepairCandidate, PolicyPatch

class PolicyProposer:
    def __init__(self, locked_paths: list[str]):
        """
        locked_paths defines paths that cannot be touched (e.g. schemas, label space, benchmark manifests)
        """
        self.locked_paths = locked_paths
        
    def propose_repair(self, cluster: ErrorCluster, parent_version: str, patch_data: dict) -> RepairCandidate:
        """
        Generates a repair candidate ensuring constraints are met.
        """
        if not cluster.case_ids:
            raise ValueError("Unconfirmed error: no case IDs")
            
        target_path = patch_data.get("target_path")
        if any(locked in target_path for locked in self.locked_paths):
            raise ValueError(f"Banned patch path: {target_path} is locked.")
            
        patch = PolicyPatch(
            patch_type=patch_data["patch_type"],
            target_path=target_path,
            diff_content=patch_data["diff_content"]
        )
        
        return RepairCandidate(
            id=f"repair-{cluster.id}",
            parent_version=parent_version,
            hypothesis=patch_data.get("hypothesis", "Fix confusion"),
            supporting_case_ids=cluster.case_ids,
            patches=[patch],
            expected_benefit="Increase macro F1",
            risk="Might overfit to development set",
            paper_reference="Dev et al., 2026 (R4)"
        )
