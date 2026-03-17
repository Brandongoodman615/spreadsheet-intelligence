from app.schemas.query import QueryPlan, QueryResult, Attribution


def build_attribution(plan: QueryPlan, result: QueryResult) -> Attribution:
    """
    Build source attribution from the query plan and execution result.
    Shows the user exactly which sheets and columns contributed to the answer.
    """
    return result.attribution
