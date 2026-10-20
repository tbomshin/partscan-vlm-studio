# -*- coding: utf-8 -*-
"""
End-to-End PoC Test Runner for Local VLM-Native Parts Inspection Studio
========================================================================
이 스크립트는 새로운 2단계 아키텍처:
  [1단계: Jeff-Gemma4-E2B VLM] ➔ [2단계: DuckDB 지식 대조 & 크롤링 보완 & 감사]
가 기존의 난제 케이스를 얼마나 완벽하고 우아하게 해결하는지 실증합니다.
"""

import sys
import os
import json

# 프로젝트 경로 설정
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vlm_engine import JeffGemmaVlmEngine
from database_engine import ModernCatalogDatabase
from enrichment_engine import KnowledgeEnrichmentEngine
from audit_validator import DeterministicAuditValidator


def run_test_case(title: str, image_path: str, vlm: JeffGemmaVlmEngine, enrichment: KnowledgeEnrichmentEngine):
    print(f"\n{'='*70}")
    print(f"▶ [테스트 실행] {title}")
    print(f"  - 대상 파일: {os.path.basename(image_path)}")
    print(f"{'='*70}")

    # 1단계: VLM 시각 인지 (Perception)
    print("\n[1단계: 로컬 Jeff-Gemma4-E2B VLM 판독 결과]")
    vlm_raw = vlm.infer_image(image_path)
    print(f"  * 메인 브랜드: {vlm_raw.primary_brand}")
    print(f"  * 서브/유통사 브랜드: {vlm_raw.secondary_brands}")
    print(f"  * 부품번호 (MFR): {vlm_raw.mfr_code}")
    print(f"  * 정품번호 (OEM): {vlm_raw.oem_code}")
    print(f"  * 교차참조 (CROSS): {vlm_raw.cross_codes}")
    print(f"  * 라벨 원문명: {vlm_raw.label_part_name}")
    print(f"  * 격리된 노이즈: {vlm_raw.ignored_noise}")

    # 2단계 A: 지식 대조 및 크롤링 보완 (Enrichment)
    print("\n[2단계 A: 카탈로그 대조 & 크롤링 보완]")
    enriched = enrichment.enrich(vlm_raw)
    print(f"  * 지식 출처: {enriched.data_source}")
    print(f"  * 카탈로그 검증 여부: {enriched.catalog_verified}")
    print(f"  * 보완된 표준 부품명: {enriched.part_name_standard}")
    print(f"  * 적용 차종 정보: {enriched.vehicle_compatibility}")

    # 2단계 B: 결정론적 규격 감사 (Audit)
    print("\n[2단계 B: 결정론적 품질 감사 결과]")
    audit = DeterministicAuditValidator.validate(vlm_raw, enriched)
    print(f"  * 감사 통과: {'✅ PASS' if audit.passed else '❌ FAIL'}")
    if audit.healed_actions:
        for action in audit.healed_actions:
            print(f"  * 자가 치유 조치: {action}")

    print("\n[최종 검수 입력폼 자동 배정 결과]")
    fields = audit.final_fields
    print(f"  ┌─ [브랜드]   : {fields['brand']}")
    print(f"  ├─ [부품번호] : {fields['mfr_code']}")
    print(f"  ├─ [정품번호] : {fields['oem_code']}")
    print(f"  └─ [부품명]   : {fields['part_name']}")


def main():
    print("======================================================================")
    print("  Local VLM-Native 2-Stage Architecture PoC Verification")
    print("  Engine: Jeff-Gemma4-E2B + DuckDB/SQLite Dual-Storage")
    print("======================================================================")

    # 1. 컴포넌트 초기화
    db = ModernCatalogDatabase()
    vlm = JeffGemmaVlmEngine()
    enrichment = KnowledgeEnrichmentEngine(db)

    # 케이스 1: 20260905_012550.jpg (표 형태 라벨, CODE# / OEM# / CROSS# 분리 및 ISO 9001 노이즈 격리)
    run_test_case(
        title="케이스 1: 복합 표 라벨 (CODE# / OEM# 분리 & ISO 9001 노이즈 차단)",
        image_path="c:/Users/taebom/Pictures/OCRtest/20260905_012550.jpg",
        vlm=vlm,
        enrichment=enrichment
    )

    # 케이스 2: 20260905_011821.jpg (폭스바겐 순정 박스 + 구석 topran 유통사 스티커)
    run_test_case(
        title="케이스 2: 브랜드 충돌 방어 (순정 VAG 메인 박스 vs 구석 topran 스티커)",
        image_path="c:/Users/taebom/Pictures/OCRtest/20260905_011821.jpg",
        vlm=vlm,
        enrichment=enrichment
    )

    # 케이스 3: 신규 미등록 품번 (크롤러 비동기 자동 보완 시뮬레이션)
    class NewPartMock:
        pass
    mock_new = JeffGemmaVlmEngine()
    def mock_infer(_):
        from schemas import VlmRawExtraction
        return VlmRawExtraction(
            primary_brand="MANN-FILTER",
            secondary_brands=[],
            mfr_code="C 30 005",
            oem_code=None,  # 박스에 순정번호가 안 적혀 있는 실제 상황
            cross_codes=[],
            label_part_name="Air Filter",
            is_container=False,
            container_marker=None,
            ignored_noise=["1 PCS"],
            visual_confidence=0.99
        )
    mock_new.infer_image = mock_infer

    run_test_case(
        title="케이스 3: 라벨에 OE가 없는 신규 품번 ➔ 외부 크롤러가 순정품번/차종 자동 보완",
        image_path="dummy_new_part.jpg",
        vlm=mock_new,
        enrichment=enrichment
    )


if __name__ == "__main__":
    main()
