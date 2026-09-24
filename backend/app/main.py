import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.config import settings
from app.database.collections import ensure_indexes
from app.api.routes import profile, assessment, fingerprint, solutions, scenarios, transformation, impact, reports, ai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ClimaCred AI API",
    description="""
ClimaCred AI - AI-powered Climate Transformation Intelligence platform for SMEs.

**Core Principle**: NOT a simple solar recommendation system. Multi-dimensional evaluation across Energy, Water, Waste, Emissions, Mobility, Materials, Operations.

**Flow**: Business Data → Climate Fingerprint → Multi-Dimensional Problem Detection → Personalized Green Interventions → Financial + Environmental Scenario Simulation → Transformation Roadmap → Impact Verification → Climate Report

All estimated metrics expose assumptions; calculated metrics retain inputs. Scores are decision-support, not certified.
""",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS
origins = settings.cors_origins_list
if not origins:
    origins = ["*"]
logger.info(f"CORS origins: {origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP {exc.status_code} on {request.url.path}: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "path": str(request.url.path)})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body": exc.body})

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "error": str(exc)})

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting ClimaCred AI API env={settings.APP_ENV} db={settings.MONGODB_DATABASE}")
    logger.info(f"Scoring weights: Energy {settings.WEIGHT_ENERGY}, Water {settings.WEIGHT_WATER}, Waste {settings.WEIGHT_WASTE}, Emissions {settings.WEIGHT_EMISSIONS}, Mobility {settings.WEIGHT_MOBILITY}, Operations {settings.WEIGHT_OPERATIONS}")
    try:
        ensure_indexes()
    except Exception as e:
        logger.warning(f"Could not ensure indexes at startup: {e}")

@app.get("/", summary="Health check & API info", tags=["System"])
async def root():
    return {
        "name": "ClimaCred AI API",
        "team": "TerraMind",
        "version": "2.0.0 (Phase 2)",
        "phase": "Phase 2 Full-Stack",
        "environment": settings.APP_ENV,
        "calculation_version": settings.CALCULATION_VERSION,
        "docs": "/docs",
        "endpoints": [
            "/api/profile",
            "/api/assessment",
            "/api/climate-fingerprint",
            "/api/solutions",
            "/api/scenarios/simulate",
            "/api/transformation-plan",
            "/api/impact",
            "/api/reports/climate",
            "/api/ai/dashboard-insights"
        ],
        "disclaimer": "ClimaCred AI scores are decision-support metrics, not official environmental certifications. All estimated metrics expose assumptions."
    }

@app.get("/health", summary="Health check", tags=["System"])
async def health():
    from app.database.mongodb import get_database, is_mock_db
    try:
        db = get_database()
        # ping
        db.command("ping")
        db_status = "connected (mock)" if is_mock_db() else "connected"
    except Exception as e:
        db_status = f"error: {e}"
    return {
        "status": "ok",
        "database": db_status,
        "calculation_version": settings.CALCULATION_VERSION,
        "environment": settings.APP_ENV
    }

# Include routers at both /api and /api/v1 for compatibility, and also bare for frontend that may use /api/...
# Profile
app.include_router(profile.router, prefix="/api/profile")
app.include_router(profile.router, prefix="/api/v1/profile")
# Assessment
app.include_router(assessment.router, prefix="/api/assessment")
app.include_router(assessment.router, prefix="/api/v1/assessment")
# Fingerprint
app.include_router(fingerprint.router, prefix="/api/climate-fingerprint")
app.include_router(fingerprint.router, prefix="/api/v1/climate-fingerprint")
# Solutions (catalog)
app.include_router(solutions.router, prefix="/api/solutions")
app.include_router(solutions.router, prefix="/api/v1/solutions")
# Also alias for spec naming: green_solutions vs solutions. For robustness add alias routes
app.include_router(solutions.router, prefix="/api/green-solutions")
# Scenarios
app.include_router(scenarios.router, prefix="/api/scenarios")
app.include_router(scenarios.router, prefix="/api/v1/scenarios")
# Frontend spec uses /api/scenario/simulate singular? We handle both via alias mounts
app.include_router(scenarios.router, prefix="/api/scenario")
# Transformation plan
app.include_router(transformation.router, prefix="/api/transformation-plan")
app.include_router(transformation.router, prefix="/api/v1/transformation-plan")
# Impact
app.include_router(impact.router, prefix="/api/impact")
app.include_router(impact.router, prefix="/api/v1/impact")
app.include_router(impact.router, prefix="/api/impact/verification")  # for frontend that may call deeper?
# Reports
app.include_router(reports.router, prefix="/api/reports")
app.include_router(reports.router, prefix="/api/v1/reports")
# AI intelligence (Gemini) - reads existing stored data, never exposed to the frontend
app.include_router(ai.router, prefix="/api/ai")
app.include_router(ai.router, prefix="/api/v1/ai")
# Also direct /api/reports/climate mounts via prefix /api/reports above handles /api/reports/climate

# Additional top-level aliases to match spec exactly without plural confusion
# e.g., spec says GET /api/profile , PATCH etc. Already covered via /api/profile
# Provide also /api/climate_fingerprint underscore alias?
# Not needed.

# For debugging, log routes on startup
@app.on_event("startup")
async def log_routes():
    for route in app.routes:
        if hasattr(route, "path"):
            logger.debug(f"Route: {route.path} [{','.join(route.methods) if hasattr(route,'methods') else ''}]")
