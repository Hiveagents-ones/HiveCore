# -*- coding: utf-8 -*-
"""Delivery stack definitions (Section II.5)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IntentLayer:
    description: str = "意图识别"

    def run(self, utterance: str) -> str:
        return utterance.strip()


@dataclass
class SlaLayer:
    description: str = "交付与验收标准化"

    def validate(self, proposal: str) -> bool:
        return bool(proposal)


@dataclass
class SupervisionLayer:
    description: str = "多轮次/垂直Agent监督"

    def gate(self, artifact: str) -> str:
        return artifact


@dataclass
class CollaborationLayer:
    description: str = "多Agent协作"

    def sync(self, summary: str) -> str:
        return summary


@dataclass
class ExperienceLayer:
    description: str = "降低用户门槛"

    def contextualize(self, message: str) -> str:
        return message


@dataclass
class DeliveryStack:
    intent: IntentLayer
    sla: SlaLayer
    supervision: SupervisionLayer
    collaboration: CollaborationLayer
    experience: ExperienceLayer

    def execute(self, utterance: str) -> str:
        processed = self.intent.run(utterance)
        if not self.sla.validate(processed):
            raise ValueError("SLA validation failed")
        supervised = self.supervision.gate(processed)
        collaborative = self.collaboration.sync(supervised)
        return self.experience.contextualize(collaborative)
