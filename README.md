# PartScan VLM Studio (v3.0 Clean-Slate)
> **온프레미스 2단계 VLM 기반 자동차 부품 비전 판독 및 검수 스튜디오**  
> **타겟 머신**: AMD Ryzen 7 5800X3D / 32GB RAM / AMD Radeon RX Vega 64 (8GB HBM2)  
> **핵심 엔진**: On-Premise `Jeff-Gemma4-E2B` (Vulkan / DirectML 가속)

---

## 1. 프로젝트 개요
본 프로젝트는 기존의 4,500줄 이상의 복잡한 수작업 휴리스틱(수백 개의 불용어 사전, 정규식, 접두사 플라이휠, 256개 브랜드 투표기)을 **완전히 배제(Clean-Slate)**하고,
로컬 VLM의 시각 인지 능력과 현대적 데이터베이스(DuckDB + SQLite WAL)를 결합한 **순수 2단계(시각 인지 -> 지식 보완/감사)** 아키텍처로 새롭게 시작하는 프로젝트입니다.

---

## 2. 핵심 아키텍처
1. **1단계 (시각 인지)**: `Jeff-Gemma4-E2B`가 Vega 64 8GB VRAM(484 GB/s)에 상주하여 0.3초 만에 표 구조와 브랜드 위계를 완벽히 분리.
2. **2단계 (지식 대조 & 크롤링 보완)**: VLM이 검증한 깨끗한 품번을 기반으로 DuckDB 및 외부 크롤러(REPXPERT/TecDoc)를 통해 보이지 않는 순정품번과 한글 표준 부품명을 결합.

---

## 3. 핵심 문서 링크
* **[제품 요구사항 정의서 (PRD)](./PRD_VLM_DESKTOP_STUDIO.md)**: 전체 시스템 및 데이터 파이프라인 상세 명세
* **[통합 도메인 지식 명세서](./CONSOLIDATED_DOMAIN_KNOWLEDGE_SPEC.md)**: VAG 6자리(`clean[3:9]`), BMW, 벤츠, 필터 4대 천왕, 섀시/제동 규격 단일 진실 원천(SSOT)
* **[데스크탑 이전 셋업 가이드](./docs/이전셋업가이드.md)**: 5800X3D + Vega 64 Vulkan 런타임 설치 및 실행 가이드

---

## 4. 빠른 시작 (Quickstart)

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 2단계 VLM PoC 실증 러너 실행
python src/run_poc.py
```
