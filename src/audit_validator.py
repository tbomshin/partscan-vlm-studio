# -*- coding: utf-8 -*-
"""
Deterministic Audit Validator:
- '적극적 덮어쓰기'를 엄단하고 '형식 검증 및 불변 공증'만 수행하는 안전벨트
"""

import re
from typing import List, Dict, Any
from schemas import VlmRawExtraction, EnrichedPartData, AuditValidationResult


class DeterministicAuditValidator:
    """
    결정론적 품질 감사기
    - VLM이 읽은 텍스트를 임의로 훼손하지 않는 비파괴적(Non-Destructive) 공증 수행
    - 순수 문법 정규화(공백 1칸, 렘포더 01 복원)만 결정론적으로 허용
    """

    @classmethod
    def validate(cls, vlm_raw: VlmRawExtraction, enriched: EnrichedPartData) -> AuditValidationResult:
        findings = []
        healed_actions = []
        
        final_brand = enriched.brand
        final_mfr = enriched.mfr_code
        final_oem = enriched.oem_code
        final_name = enriched.part_name_standard

        # 1. 렘포더(LEMFÖRDER) 7자리 표준화 (5자리 단편 시 01 기본 복원)
        if final_brand.upper() == "LEMFÖRDER" or "LEMF" in final_brand.upper():
            clean_mfr = re.sub(r"[^0-9]", "", final_mfr)
            if len(clean_mfr) == 5:
                final_mfr = f"{clean_mfr} 01"
                healed_actions.append(f"LEMFÖRDER 5자리 단편({clean_mfr}) ➔ 공식 7자리({final_mfr}) 규격 복원")

        # 2. 메르세데스-벤츠 A 접두사 보장
        if "MERCEDES" in final_brand.upper() or "BENZ" in final_brand.upper():
            if final_oem and not final_oem.startswith("A") and len(re.sub(r"[^0-9]", "", final_oem)) >= 10:
                final_oem = f"A {final_oem}"
                healed_actions.append(f"MERCEDES-BENZ 공인 접두사 A 결합: {final_oem}")

        # 3. 불용어 및 인증 규격 침범 여부 안전 검사
        forbidden_terms = ["ISO9001", "ISO 9001", "TS16949", "1STUECK", "PIECE", "MADE IN"]
        for term in forbidden_terms:
            if final_mfr and term in final_mfr.upper().replace(" ", ""):
                findings.append(f"CRITICAL: 불용어({term})가 부품번호에 포함됨")
                final_mfr = "-"
            if final_oem and term in final_oem.upper().replace(" ", ""):
                findings.append(f"CRITICAL: 불용어({term})가 순정품번에 포함됨")
                final_oem = "-"

        # 4. 물류 겉박스(#) 자격 검증
        is_container_final = vlm_raw.is_container
        if is_container_final and (final_mfr != "-" or final_oem != "-"):
            is_container_final = False
            healed_actions.append("부품 정보가 존재하는 이미지의 허위 겉박스(#) 판정 기각 ➔ 부품 모드로 강제 정상화")

        final_fields = {
            "brand": final_brand,
            "mfr_code": final_mfr,
            "oem_code": final_oem,
            "part_name": final_name,
            "is_container": is_container_final,
            "catalog_verified": enriched.catalog_verified,
            "data_source": enriched.data_source,
            "vehicle_compatibility": enriched.vehicle_compatibility
        }

        return AuditValidationResult(
            passed=len(findings) == 0,
            final_fields=final_fields,
            findings=findings,
            healed_actions=healed_actions,
            immutable_vlm_backup=vlm_raw
        )
