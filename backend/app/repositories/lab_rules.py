"""Explicit-ID and explicit-version persistence reads for B4 rule authority."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import or_, select

from app.models.lab_rules import (
    LabKnowledgeRule,
    LabRuleCompilationRun,
    LabRuleContradiction,
    LabRuleGroup,
    LabRuleGroupMember,
    LabRuleSupportEvidence,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class LabRuleRepositoryMixin:
    if TYPE_CHECKING:
        session: AsyncSession

    async def get_rule_group(self, group_id: str) -> LabRuleGroup | None:
        return await self.session.get(LabRuleGroup, group_id)

    async def rule_group_by_key_version(
        self,
        group_key: str,
        version: int,
    ) -> LabRuleGroup | None:
        result = await self.session.execute(
            select(LabRuleGroup).where(
                LabRuleGroup.group_key == group_key,
                LabRuleGroup.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def rule_group_by_hash(
        self,
        content_sha256: str,
    ) -> LabRuleGroup | None:
        result = await self.session.execute(
            select(LabRuleGroup).where(
                LabRuleGroup.content_sha256 == content_sha256
            )
        )
        return result.scalar_one_or_none()

    async def rule_group_members(
        self,
        group_id: str,
    ) -> list[LabRuleGroupMember]:
        result = await self.session.execute(
            select(LabRuleGroupMember)
            .where(LabRuleGroupMember.group_id == group_id)
            .order_by(LabRuleGroupMember.position, LabRuleGroupMember.id)
        )
        return list(result.scalars())

    async def rule_group_member_by_hash(
        self,
        content_sha256: str,
    ) -> LabRuleGroupMember | None:
        result = await self.session.execute(
            select(LabRuleGroupMember).where(
                LabRuleGroupMember.content_sha256 == content_sha256
            )
        )
        return result.scalar_one_or_none()

    async def get_knowledge_rule(
        self,
        rule_id: str,
    ) -> LabKnowledgeRule | None:
        return await self.session.get(LabKnowledgeRule, rule_id)

    async def knowledge_rule_by_key_version(
        self,
        rule_key: str,
        version: int,
    ) -> LabKnowledgeRule | None:
        result = await self.session.execute(
            select(LabKnowledgeRule).where(
                LabKnowledgeRule.rule_key == rule_key,
                LabKnowledgeRule.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def knowledge_rule_by_hash(
        self,
        content_sha256: str,
    ) -> LabKnowledgeRule | None:
        result = await self.session.execute(
            select(LabKnowledgeRule).where(
                LabKnowledgeRule.content_sha256 == content_sha256
            )
        )
        return result.scalar_one_or_none()

    async def get_rule_contradiction(
        self,
        contradiction_id: str,
    ) -> LabRuleContradiction | None:
        return await self.session.get(LabRuleContradiction, contradiction_id)

    async def contradictions_for_rule(
        self,
        rule_id: str,
    ) -> list[LabRuleContradiction]:
        result = await self.session.execute(
            select(LabRuleContradiction)
            .where(
                or_(
                    LabRuleContradiction.rule_id == rule_id,
                    LabRuleContradiction.contradictory_rule_id == rule_id,
                )
            )
            .order_by(
                LabRuleContradiction.rule_id,
                LabRuleContradiction.contradictory_rule_id,
                LabRuleContradiction.reason_code,
            )
        )
        return list(result.scalars())

    async def rule_contradiction_by_pair_reason(
        self,
        rule_id: str,
        contradictory_rule_id: str,
        reason_code: str,
    ) -> LabRuleContradiction | None:
        result = await self.session.execute(
            select(LabRuleContradiction).where(
                LabRuleContradiction.rule_id == rule_id,
                LabRuleContradiction.contradictory_rule_id
                == contradictory_rule_id,
                LabRuleContradiction.reason_code == reason_code,
            )
        )
        return result.scalar_one_or_none()

    async def rule_contradiction_by_hash(
        self,
        content_sha256: str,
    ) -> LabRuleContradiction | None:
        result = await self.session.execute(
            select(LabRuleContradiction).where(
                LabRuleContradiction.content_sha256 == content_sha256
            )
        )
        return result.scalar_one_or_none()

    async def get_rule_support(
        self,
        support_id: str,
    ) -> LabRuleSupportEvidence | None:
        return await self.session.get(LabRuleSupportEvidence, support_id)

    async def supports_for_rule(
        self,
        rule_id: str,
    ) -> list[LabRuleSupportEvidence]:
        result = await self.session.execute(
            select(LabRuleSupportEvidence)
            .where(LabRuleSupportEvidence.rule_id == rule_id)
            .order_by(
                LabRuleSupportEvidence.support_kind,
                LabRuleSupportEvidence.reference_id,
                LabRuleSupportEvidence.id,
            )
        )
        return list(result.scalars())

    async def rule_support_by_hash(
        self,
        content_sha256: str,
    ) -> LabRuleSupportEvidence | None:
        result = await self.session.execute(
            select(LabRuleSupportEvidence).where(
                LabRuleSupportEvidence.content_sha256 == content_sha256
            )
        )
        return result.scalar_one_or_none()

    async def get_rule_compilation(
        self,
        compilation_id: str,
    ) -> LabRuleCompilationRun | None:
        return await self.session.get(LabRuleCompilationRun, compilation_id)

    async def rule_compilation_by_hash(
        self,
        content_sha256: str,
    ) -> LabRuleCompilationRun | None:
        result = await self.session.execute(
            select(LabRuleCompilationRun).where(
                LabRuleCompilationRun.content_sha256 == content_sha256
            )
        )
        return result.scalar_one_or_none()


__all__ = ["LabRuleRepositoryMixin"]
