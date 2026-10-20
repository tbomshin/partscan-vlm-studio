# -*- coding: utf-8 -*-
"""
PoC Schemas for Local VLM-Native Parts Inspection Studio
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VlmRawExtraction(BaseModel):
    """1단계: 로컬 VLM (Jeff-Gemma4-E2B)이 라벨에서 직접 추출한 순수 시각 팩트"""
    primary_brand: str = Field(..., description="메인 제조사 브랜드 (예: AUDI, VW, MANN-FILTER)")
    secondary_brands: List[str] = Field(default_factory=list, description="유통사/협력사 스티커 브랜드 (예: TOPRAN)")
    mfr_code: Optional[str] = Field(None, description="제조사/애프터마켓 품번 (예: CVK630, C 30 005)")
    oem_code: Optional[str] = Field(None, description="완성차 순정 품번 (예: 4B0 819 439 C)")
    cross_codes: List[str] = Field(default_factory=list, description="교차 참조 호환 품번 목록 (예: CUK 3037)")
    label_part_name: Optional[str] = Field(None, description="라벨에 인쇄된 원문 부품명 (예: CABIN AIR FILTER, OELFILTER)")
    is_container: bool = Field(False, description="물류 겉박스(#) 여부 (부품 정보가 있으면 무조건 False)")
    container_marker: Optional[str] = Field(None, description="겉박스 관리번호 (예: #001, #019)")
    ignored_noise: List[str] = Field(default_factory=list, description="부품번호에서 제외된 인증/단위 노이즈 (예: ISO 9001, 1 STUECK)")
    visual_confidence: float = Field(0.95, ge=0.0, le=1.0, description="시각적 판독 신뢰도")


class EnrichedPartData(BaseModel):
    """2단계 A: 카탈로그 대조 및 외부 크롤링을 통해 '보이지 않는 지식'을 채운 완성 데이터"""
    brand: str
    mfr_code: str
    oem_code: str
    part_name_standard: str = Field(..., description="200대 공식 분류체계 표준 부품명 (예: CABIN FILTER 에어컨필터)")
    vehicle_compatibility: List[str] = Field(default_factory=list, description="적용 차종 (예: AUDI A4 B6/B7, A6 C5)")
    data_source: str = Field(..., description="지식 획득 경로 (LOCAL_CATALOG_HIT, CRAWLED_REPXPERT, NEW_UNVERIFIED)")
    catalog_verified: bool = Field(False, description="공식 카탈로그 실존 검증 여부")


class AuditValidationResult(BaseModel):
    """2단계 B: 결정론적 규격 감사 결과"""
    passed: bool
    final_fields: Dict[str, Any]
    findings: List[str] = Field(default_factory=list)
    healed_actions: List[str] = Field(default_factory=list)
    immutable_vlm_backup: VlmRawExtraction
