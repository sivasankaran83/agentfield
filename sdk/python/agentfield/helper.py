"""
Test code with intentional issues for PR Reviewer Agent
"""

def authenticate_user(username, password):
    """Authenticate user - HAS ISSUES!"""
    
    # SECURITY ISSUE: SQL Injection
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    
    # ERROR: Division by zero possible
    result = calculate_score(10, 0)
    
    # QUALITY: Missing error handling
    db_result = execute_query(query)
    
    return db_result


def calculate_score(points, games):
    """Calculate average score"""
    # No validation!
    return points / games


def execute_query(query):
    """Execute database query"""
    # TODO: Implement this
    pass


