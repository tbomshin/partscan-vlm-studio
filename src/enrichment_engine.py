# -*- coding: utf-8 -*-
"""
Stage 2 Engine: Knowledge Grounding & Crawling Enrichment
VLM이 추출한 시각 팩트를 기반으로 카탈로그 대조, 외부 크롤링 보완 및 200대 표준 컨벤션 결합
"""

import re
from typing import Optional
from schemas import VlmRawExtraction, EnrichedPartData
from database_engine import ModernCatalogDatabase


class KnowledgeEnrichmentEngine:
    """
    지식 대조 및 크롤링 보완 엔진
    - Clean In -> Clean Out 원칙: VLM이 검증한 깨끗한 품번으로만 조회하여 오염 차단
    """

    def __init__(self, db: ModernCatalogDatabase):
        self.db = db

    def enrich(self, vlm_data: VlmRawExtraction) -> EnrichedPartData:
        """
        VLM 추출 데이터를 받아 내부 DB 및 외부 크롤링을 통해 '보이지 않는 지식'을 채움
        """
        # 1. 1순위: 내부 마스터 DB 대조 (MFR 품번 또는 OEM 품번)
        cat_hit = None
        for code in [vlm_data.mfr_code, vlm_data.oem_code] + vlm_data.cross_codes:
            if code:
                cat_hit = self.db.query_cross_reference(code)
                if cat_hit:
                    break

        if cat_hit:
            # 내부 DB에서 호환 순정품번, 차종, 표준 부품명 즉시 결합
            final_brand = cat_hit["brand"] or vlm_data.primary_brand
            final_mfr = vlm_data.mfr_code or cat_hit["mfr_code"]
            final_oem = vlm_data.oem_code or cat_hit["oem_code"]
            final_name = cat_hit["standard_part_name"]
            
            return EnrichedPartData(
                brand=final_brand,
                mfr_code=final_mfr or "-",
                oem_code=final_oem or "-",
                part_name_standard=final_name,
                vehicle_compatibility=[cat_hit["vehicle_application"]],
                data_source="LOCAL_CATALOG_HIT",
                catalog_verified=True
            )

        # 2. 2순위: 내부 DB에 없는 신규 품번 -> 외부 크롤러(REPXPERT/TecDoc) 비동기 조회
        crawled = self._crawler_fallback_hook(vlm_data)
        if crawled:
            # 크롤러가 찾아온 지식을 내부 DB에 영구 저장(캐싱)
            self.db.insert_new_knowledge(
                brand=crawled["brand"],
                mfr_code=crawled["mfr_code"],
                oem_code=crawled["oem_code"],
                standard_part_name=crawled["standard_part_name"],
                vehicle_app=crawled["vehicle_application"],
                source="CRAWLER_AUTO_DISCOVERED"
            )
            return EnrichedPartData(
                brand=crawled["brand"],
                mfr_code=crawled["mfr_code"],
                oem_code=crawled["oem_code"],
                part_name_standard=crawled["standard_part_name"],
                vehicle_compatibility=[crawled["vehicle_application"]],
                data_source="CRAWLED_REPXPERT",
                catalog_verified=True
            )

        # 3. 3순위: 크롤링도 미지원되는 특수 품번 -> 제조사 기능그룹 문법(VAG [3:9] 등) 0초 디코딩
        decoded_name = self._decode_oem_functional_group(vlm_data.oem_code or vlm_data.mfr_code)
        
        return EnrichedPartData(
            brand=vlm_data.primary_brand,
            mfr_code=vlm_data.mfr_code or "-",
            oem_code=vlm_data.oem_code or "-",
            part_name_standard=decoded_name or vlm_data.label_part_name or "AUTO PART",
            vehicle_compatibility=[],
            data_source="OEM_SYNTAX_DECODED" if decoded_name else "NEW_UNVERIFIED",
            catalog_verified=bool(decoded_name)
        )

    def _crawler_fallback_hook(self, vlm_data: VlmRawExtraction) -> Optional[dict]:
        """
        외부 카탈로그 크롤러(REPXPERT CDP, TecDoc, AutoDoc) 연동 훅
        (PoC에서는 실연을 위한 안전한 모의 크롤러 응답 제공)
        """
        target_code = vlm_data.mfr_code or vlm_data.oem_code
        if not target_code:
            return None
            
        norm = target_code.replace(" ", "").upper()
        
        # 외부 크롤러가 실시간으로 찾아내는 케이스 모의
        if "C30005" in norm:
            return {
                "brand": "MANN-FILTER",
                "mfr_code": "C 30 005",
                "oem_code": "13 71 7 532 754",
                "standard_part_name": "AIR FILTER 에어필터",
                "vehicle_application": "BMW 3 Series (E90), 5 Series (E60)"
            }
        return None

    def _decode_oem_functional_group(self, code: Optional[str]) -> Optional[str]:
        """
        VAG 6자리 clean[3:9] 및 BMW HG/UG 기능 그룹 규칙 0초 디코딩
        """
        if not code:
            return None
            
        norm = re.sub(r"[^A-Z0-9]", "", code.upper())
        
        # VAG 6자리 (digits 4 to 9) 규칙
        if len(norm) >= 9 and norm[0].isdigit() or norm[0] in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            sub6 = norm[3:9] if len(norm) >= 9 else ""
            vag_map = {
                "115561": "FILTER 오일필터",
                "121058": "HOSE 냉각수호스",
                "121011": "W/PUMP 워터펌프",
                "121111": "THERMOSTAT 써모스탯",
                "129620": "AIR FILTER 에어필터",
                "412065": "MOUNT 쇼바마운트",
                "498811": "END 타이로드엔드KIT",
                "498625": "BEARING 휠베어링KIT",
                "615301": "DISC 브레이크디스크",
                "698151": "PAD 브레이크패드KIT",
                "819439": "CABIN FILTER 에어컨필터"
            }
            if sub6 in vag_map:
                return vag_map[sub6]
                
        return None
