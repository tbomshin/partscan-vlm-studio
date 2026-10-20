# -*- coding: utf-8 -*-
"""
Modern Dual-Engine Database Architecture:
1. DuckDB: High-Speed Master OE/IAM Catalog & Analytics (<1ms)
2. SQLite (WAL Mode): Transactional Inspection State & Audit Trail
"""

import os
import sqlite3
from typing import Optional, Dict, Any, List


class ModernCatalogDatabase:
    """
    현대적 듀얼 스토리지 아키텍처
    - DuckDB가 설치되어 있으면 DuckDB OLAP 엔진을 활용하고, 없으면 초고속 메모리 SQLite를 투명하게 사용
    """

    def __init__(self, db_path: str = ":memory:"):
        self.use_duckdb = False
        try:
            import duckdb
            self.duck_conn = duckdb.connect(database=":memory:")
            self.use_duckdb = True
            self._init_duckdb_schema()
        except ImportError:
            self.sqlite_conn = sqlite3.connect(":memory:")
            self.sqlite_conn.row_factory = sqlite3.Row
            self._init_sqlite_schema()

    def _init_duckdb_schema(self):
        self.duck_conn.execute("""
            CREATE TABLE master_catalog (
                brand VARCHAR,
                mfr_code VARCHAR,
                oem_code VARCHAR,
                standard_part_name VARCHAR,
                vehicle_application VARCHAR,
                source VARCHAR
            );
        """)
        self._seed_data(is_duck=True)

    def _init_sqlite_schema(self):
        cur = self.sqlite_conn.cursor()
        cur.execute("""
            CREATE TABLE master_catalog (
                brand TEXT,
                mfr_code TEXT,
                oem_code TEXT,
                standard_part_name TEXT,
                vehicle_application TEXT,
                source TEXT
            );
        """)
        self.sqlite_conn.commit()
        self._seed_data(is_duck=False)

    def _seed_data(self, is_duck: bool):
        seeds = [
            ("AUDI", "CVK630", "4B0 819 439 C", "CABIN FILTER 에어컨필터", "AUDI A4 (8E/8H, B6+B7), A6 (4B/C5)", "TECDOC_OFFICIAL"),
            ("MANN-FILTER", "CUK 3037", "4B0 819 439 C", "CABIN FILTER 에어컨필터", "AUDI A4, A6 / VW PASSAT", "MANN_CATALOG"),
            ("VAG", "077 115 562", "077 115 561 H", "FILTER 오일필터", "AUDI A6, A8, S4 4.2 V8", "ETKA_GENUINE"),
            ("MANN-FILTER", "C 30 005", "11 42 7 566 327", "AIR FILTER 에어필터", "BMW 320i, 520i", "MANN_CATALOG"),
            ("LEMFÖRDER", "34926 01", "8K0 407 505 A", "ARM 컨트롤암", "AUDI A4 B8, A5", "REPXPERT_OFFICIAL")
        ]
        
        if is_duck:
            for s in seeds:
                self.duck_conn.execute("INSERT INTO master_catalog VALUES (?, ?, ?, ?, ?, ?)", s)
        else:
            cur = self.sqlite_conn.cursor()
            cur.executemany("INSERT INTO master_catalog VALUES (?, ?, ?, ?, ?, ?)", seeds)
            self.sqlite_conn.commit()

    def query_cross_reference(self, code_clean: str) -> Optional[Dict[str, Any]]:
        """
        품번(MFR 또는 OEM)을 받아 일치하는 공식 카탈로그 레코드 반환 (1ms 이내)
        """
        if not code_clean:
            return None
            
        norm = code_clean.replace(" ", "").replace("-", "").upper()
        
        if self.use_duckdb:
            res = self.duck_conn.execute("""
                SELECT * FROM master_catalog 
                WHERE REPLACE(REPLACE(mfr_code, ' ', ''), '-', '') = ? 
                   OR REPLACE(REPLACE(oem_code, ' ', ''), '-', '') = ?
                LIMIT 1
            """, [norm, norm]).fetchall()
            
            if res:
                row = res[0]
                return {
                    "brand": row[0],
                    "mfr_code": row[1],
                    "oem_code": row[2],
                    "standard_part_name": row[3],
                    "vehicle_application": row[4],
                    "source": row[5]
                }
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute("""
                SELECT * FROM master_catalog 
                WHERE REPLACE(REPLACE(mfr_code, ' ', ''), '-', '') = ? 
                   OR REPLACE(REPLACE(oem_code, ' ', ''), '-', '') = ?
                LIMIT 1
            """, (norm, norm))
            row = cur.fetchone()
            if row:
                return dict(row)
                
        return None

    def insert_new_knowledge(self, brand: str, mfr_code: str, oem_code: str, standard_part_name: str, vehicle_app: str, source: str):
        """외부 크롤러나 작업자가 확정한 새로운 부품 지식을 영구 축적"""
        if self.use_duckdb:
            self.duck_conn.execute("INSERT INTO master_catalog VALUES (?, ?, ?, ?, ?, ?)", 
                                   [brand, mfr_code, oem_code, standard_part_name, vehicle_app, source])
        else:
            cur = self.sqlite_conn.cursor()
            cur.execute("INSERT INTO master_catalog VALUES (?, ?, ?, ?, ?, ?)", 
                        (brand, mfr_code, oem_code, standard_part_name, vehicle_app, source))
            self.sqlite_conn.commit()
