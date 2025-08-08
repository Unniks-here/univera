from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import text
from typing import Dict, Any
from app.database import get_db
from app.auth import get_current_user
from app.models import Record

router = APIRouter()


@router.post("/report/ledger/")
def generate_ledger_report(
    report_config: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    entity = report_config.get("entity")
    filters = report_config.get("filters", {})
    group_by = report_config.get("group_by")
    aggregates = report_config.get("aggregate", [])
    include = report_config.get("include", [])
    sort_by = report_config.get("sort_by", [])
    order = report_config.get("order", "asc")

    if not entity or not group_by:
        raise HTTPException(status_code=400, detail="Missing required parameters: entity or group_by")

    params = {
        "entity": entity,
        "tenant_id": current_user.tenant_id
    }

    date_filter_sql = ""
    if "date" in filters:
        date_from = filters["date"].get("from")
        date_to = filters["date"].get("to")
        if date_from and date_to:
            date_filter_sql = "AND (r.data->>'date')::date BETWEEN :date_from AND :date_to"
            params["date_from"] = date_from
            params["date_to"] = date_to

    account_filter_sql = ""
    if "account" in filters:
        account_filter_sql = "AND LOWER(TRIM(entry->>'account')) = LOWER(TRIM(:account))"
        params["account"] = filters["account"]

    # Final query
    query = f"""
    SELECT 
        entry->>'account' AS account,
        SUM((entry->>'debit')::numeric) AS total_debit,
        SUM((entry->>'credit')::numeric) AS total_credit,
        JSON_AGG(jsonb_build_object(
            'date', r.data->>'date',
            'description', r.data->>'description',
            'reference_no', r.data->>'reference_no',
            'debit', entry->>'debit',
            'credit', entry->>'credit'
        )) AS transactions
    FROM records r,
    jsonb_path_query(r.data, '$.entries[*]') AS entry
    WHERE r.entity_name = :entity
      AND r.tenant_id = :tenant_id
      {date_filter_sql}
      {account_filter_sql}
    GROUP BY account
    ORDER BY account {order.upper()}
    """

    print("Executing SQL:", query)
    result = db.execute(text(query), params).fetchall()
    return [dict(row._mapping) for row in result]