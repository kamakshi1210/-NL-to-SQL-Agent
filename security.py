# security.py
import sqlglot
from sqlglot import exp

def validate_sql_query(sql_str: str) -> bool:
    """
    Parses the SQL string and ensures it ONLY contains safe, read-only statements.
    Raises a ValueError if any dangerous modification operation is detected.
    """
    try:
        # 1. Clean the incoming string
        clean_query = sql_str.strip().strip("`").replace("sql\n", "").strip()
        
        # 2. Parse the SQL string into statements
        parsed_statements = sqlglot.parse(clean_query)
        
        # 3. Loop through every statement
        for statement in parsed_statements:
            # ALLOW explicit SELECT statements
            if isinstance(statement, exp.Select):
                continue
                
            # ALLOW internal schema inspection tools (like LangChain's PRAGMA calls)
            if isinstance(statement, exp.Pragma):
                continue
                
            # ALLOW basic metadata calls (like command line show/describe checks)
            if type(statement).__name__.lower() in ["show", "describe"]:
                continue
                
            # If it matches nothing above (e.g., Delete, Drop, Update, Insert), BLOCK IT!
            raise ValueError(
                f"Security Guard Alert: Blocked an unauthorized database modification attempt. "
                f"Detected operation type: ({type(statement).__name__})."
            )
            
        return True
        
    except sqlglot.errors.ParseError:
        raise ValueError("Security Guard Alert: The generated SQL syntax is invalid or corrupted.")