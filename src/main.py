# #!/usr/bin/env python3
# """
# Main entry point for PDF Processing API
# """

# import uvicorn
# from backend.api.fastapi_app import app
# from config.settings import HOST, PORT

# def main():
#     """Main function to run the FastAPI application"""
#     print("🚀 Starting PDF Processing API...")
#     print(f"🌐 Server will be available at: http://{HOST}:{PORT}")
#     print("📚 API Documentation: http://{HOST}:{PORT}/docs")
#     print("🔧 Press Ctrl+C to stop the server")
#     print("=" * 50)
    
#     uvicorn.run(
#         app, 
#         host=HOST, 
#         port=PORT,
#         log_level="info"
#     )

# if __name__ == "__main__":
#     main()


import uvicorn
from backend.api.fastapi_app import app
from config.settings import HOST, PORT
import os
from dotenv import load_dotenv
load_dotenv()

def main():
    """Main function to run the FastAPI application"""
    print("🚀 Starting PDF Processing API...")
    port = int(os.getenv("PORT", PORT))
    print(f"🌐 Server will be available at: http://{HOST}:{port}")
    print(f"📚 API Documentation: http://{HOST}:{port}/docs")
    print("🔧 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    uvicorn.run(
        app, 
        host=HOST, 
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()