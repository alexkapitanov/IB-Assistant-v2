"""Environment validation utilities for IB Assistant v2"""

import os
import sys
import asyncio
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
import redis.asyncio as redis
from openai import AsyncOpenAI
import qdrant_client
from pydantic import ValidationError
from backend.settings import get_settings, REDIS_URL as DEFAULT_REDIS_URL

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of a validation check"""
    name: str
    status: str  # "pass", "warn", "fail"
    message: str
    details: Optional[str] = None

class EnvironmentValidator:
    """Validates environment configuration and external dependencies"""
    
    def __init__(self):
        self.settings = get_settings()
        self.results: List[ValidationResult] = []
    
    async def validate_all(self) -> Dict[str, any]:
        """Run all validation checks"""
        logger.info("Starting environment validation...")
        
        # Core environment checks
        await self._check_required_env_vars()
        await self._check_optional_env_vars()
        await self._check_python_version()
        
        # External service checks
        await self._check_openai_connection()
        await self._check_qdrant_connection()
        await self._check_redis_connection()
        
        # Configuration validation
        await self._check_settings_validation()
        await self._check_model_configuration()
        
        # Security checks
        await self._check_security_settings()
        
        return self._generate_report()
    
    async def _check_required_env_vars(self):
        """Check all required environment variables"""
        required_vars = [
            ("OPENAI_API_KEY", "OpenAI API key for LLM access"),
            ("QDRANT_URL", "Qdrant vector database URL"),
            ("DATA_DIR", "Directory for file storage")
        ]
        
        for var_name, description in required_vars:
            value = os.getenv(var_name)
            if not value:
                self.results.append(ValidationResult(
                    name=f"Required env var: {var_name}",
                    status="fail",
                    message=f"Missing required environment variable",
                    details=description
                ))
            elif var_name == "OPENAI_API_KEY" and not value.startswith("sk-"):
                self.results.append(ValidationResult(
                    name=f"Required env var: {var_name}",
                    status="warn",
                    message="OpenAI API key format may be invalid",
                    details="Expected format: sk-..."
                ))
            else:
                self.results.append(ValidationResult(
                    name=f"Required env var: {var_name}",
                    status="pass",
                    message="✓ Present and valid"
                ))
    
    async def _check_optional_env_vars(self):
        """Check optional environment variables with defaults"""
        optional_vars = [
            ("REDIS_URL", DEFAULT_REDIS_URL, "Redis for rate limiting"),
            ("PORT", "8000", "API server port"),
            ("QDRANT_API_KEY", None, "Qdrant authentication"),
            ("ENABLE_METRICS", "true", "Prometheus metrics"),
            ("MAX_TOKENS_PER_SESSION", "50000", "Token limit per session"),
            ("RATE_LIMIT_REQUESTS", "10", "Rate limit requests per minute")
        ]
        
        for var_name, default, description in optional_vars:
            value = os.getenv(var_name, default)
            self.results.append(ValidationResult(
                name=f"Optional env var: {var_name}",
                status="pass",
                message=f"✓ Using: {value}",
                details=description
            ))
    
    async def _check_python_version(self):
        """Check Python version compatibility"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 11:
            self.results.append(ValidationResult(
                name="Python version",
                status="pass",
                message=f"✓ Python {version.major}.{version.minor}.{version.micro}"
            ))
        elif version.major == 3 and version.minor >= 8:
            self.results.append(ValidationResult(
                name="Python version",
                status="warn",
                message=f"Python {version.major}.{version.minor}.{version.micro} - consider upgrading to 3.11+",
                details="Some features may not be available in older Python versions"
            ))
        else:
            self.results.append(ValidationResult(
                name="Python version",
                status="fail",
                message=f"Python {version.major}.{version.minor}.{version.micro} is too old",
                details="Requires Python 3.8 or higher"
            ))
    
    async def _check_openai_connection(self):
        """Test OpenAI API connection"""
        try:
            client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            # Test with a minimal request
            response = await client.models.list()
            models = [m.id for m in response.data]
            
            # Check for required models
            required_models = ["gpt-4.1", "gpt-4.1-mini", "o3-mini"]
            available_required = [m for m in required_models if m in models]
            
            if available_required:
                self.results.append(ValidationResult(
                    name="OpenAI connection",
                    status="pass",
                    message="✓ Connected successfully",
                    details=f"Available required models: {', '.join(available_required)}"
                ))
            else:
                self.results.append(ValidationResult(
                    name="OpenAI connection",
                    status="warn",
                    message="Connected but no required models found",
                    details=f"Required: {', '.join(required_models)}"
                ))
                
        except Exception as e:
            self.results.append(ValidationResult(
                name="OpenAI connection",
                status="fail",
                message="Failed to connect to OpenAI API",
                details=str(e)
            ))
    
    async def _check_qdrant_connection(self):
        """Test Qdrant vector database connection"""
        try:
            if self.settings.qdrant_api_key:
                client = qdrant_client.AsyncQdrantClient(
                    url=self.settings.qdrant_url,
                    api_key=self.settings.qdrant_api_key
                )
            else:
                client = qdrant_client.AsyncQdrantClient(url=self.settings.qdrant_url)
            
            # Test connection with health check
            health = await client.get_cluster_info()
            self.results.append(ValidationResult(
                name="Qdrant connection",
                status="pass",
                message="✓ Connected successfully",
                details=f"Cluster status: {health.status if hasattr(health, 'status') else 'OK'}"
            ))
            
        except Exception as e:
            self.results.append(ValidationResult(
                name="Qdrant connection",
                status="fail",
                message="Failed to connect to Qdrant",
                details=str(e)
            ))
    
    async def _check_redis_connection(self):
        """Test Redis connection (optional)"""
        try:
            redis_client = redis.from_url(self.settings.redis_url)
            await redis_client.ping()
            await redis_client.close()
            
            self.results.append(ValidationResult(
                name="Redis connection",
                status="pass",
                message="✓ Connected successfully",
                details="Rate limiting will use Redis"
            ))
            
        except Exception as e:
            self.results.append(ValidationResult(
                name="Redis connection",
                status="warn",
                message="Redis not available, using in-memory fallback",
                details=str(e)
            ))
    
    async def _check_settings_validation(self):
        """Validate Pydantic settings"""
        try:
            settings = get_settings()
            self.results.append(ValidationResult(
                name="Settings validation",
                status="pass",
                message="✓ All settings valid"
            ))
        except ValidationError as e:
            self.results.append(ValidationResult(
                name="Settings validation",
                status="fail",
                message="Settings validation failed",
                details=str(e)
            ))
    
    async def _check_model_configuration(self):
        """Check model configuration"""
        models = [
            self.settings.chat_model,
            self.settings.router_model,
            self.settings.expert_model
        ]
        
        approved_models = ["gpt-4.1", "gpt-4.1-mini", "o3-mini"]
        
        for model in set(models):
            if model in approved_models:
                self.results.append(ValidationResult(
                    name=f"Model config: {model}",
                    status="pass",
                    message="✓ Approved model"
                ))
            else:
                self.results.append(ValidationResult(
                    name=f"Model config: {model}",
                    status="fail",
                    message="Unapproved model in configuration",
                    details=f"Use one of: {', '.join(approved_models)}"
                ))
    
    async def _check_security_settings(self):
        """Check security-related configuration"""
        checks = [
            ("API Key length", len(self.settings.openai_api_key) >= 40, "API key should be sufficiently long"),
            ("Rate limiting", self.settings.rate_limit_requests > 0, "Rate limiting should be enabled"),
            ("Token limits", self.settings.max_tokens_per_session > 0, "Token limits should be set"),
        ]
        
        for check_name, condition, message in checks:
            if condition:
                self.results.append(ValidationResult(
                    name=f"Security: {check_name}",
                    status="pass",
                    message="✓ " + message
                ))
            else:
                self.results.append(ValidationResult(
                    name=f"Security: {check_name}",
                    status="warn",
                    message="⚠ " + message
                ))
    
    def _generate_report(self) -> Dict[str, any]:
        """Generate final validation report"""
        pass_count = sum(1 for r in self.results if r.status == "pass")
        warn_count = sum(1 for r in self.results if r.status == "warn")
        fail_count = sum(1 for r in self.results if r.status == "fail")
        
        overall_status = "fail" if fail_count > 0 else ("warn" if warn_count > 0 else "pass")
        
        return {
            "overall_status": overall_status,
            "summary": {
                "total_checks": len(self.results),
                "passed": pass_count,
                "warnings": warn_count,
                "failed": fail_count
            },
            "checks": [
                {
                    "name": r.name,
                    "status": r.status,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ]
        }

async def validate_environment() -> Dict[str, any]:
    """Main entry point for environment validation"""
    validator = EnvironmentValidator()
    return await validator.validate_all()

if __name__ == "__main__":
    async def main():
        result = await validate_environment()
        
        print("\n" + "="*60)
        print("ENVIRONMENT VALIDATION REPORT")
        print("="*60)
        
        summary = result["summary"]
        status_emoji = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
        print(f"\nOverall Status: {status_emoji[result['overall_status']]} {result['overall_status'].upper()}")
        print(f"Total Checks: {summary['total_checks']}")
        print(f"Passed: {summary['passed']}")
        print(f"Warnings: {summary['warnings']}")
        print(f"Failed: {summary['failed']}")
        
        print("\nDetailed Results:")
        print("-" * 60)
        
        for check in result["checks"]:
            emoji = status_emoji[check["status"]]
            print(f"{emoji} {check['name']}: {check['message']}")
            if check["details"]:
                print(f"   {check['details']}")
        
        print("\n" + "="*60)
        
        # Exit with appropriate code
        sys.exit(0 if result["overall_status"] == "pass" else 1)
    
    asyncio.run(main())
