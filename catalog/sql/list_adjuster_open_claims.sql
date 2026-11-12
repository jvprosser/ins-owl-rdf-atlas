SELECT
  c.claim_id,
  c.claim_number,
  c.claim_status_code,
  pe.first_name,
  pe.last_name
FROM ${database}.claim c
INNER JOIN ${database}.claim_party_role r
  ON r.claim_id = c.claim_id
 AND r.role_type_code = 'ADJUSTER'
 AND r.is_current_assignment = TRUE
 AND r.party_id = ${party_id}
LEFT JOIN ${database}.person pe ON pe.party_id = r.party_id
WHERE UPPER(COALESCE(c.claim_status_code, '')) <> 'CLOSED'
ORDER BY c.claim_id
