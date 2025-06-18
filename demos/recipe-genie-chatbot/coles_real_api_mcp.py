import os
import requests
import json
from mcp.server import FastMCP
from typing import Optional, Dict, List, Any
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get MCP server configuration from environment
MCP_HOST = os.getenv("MCP_HOST", "localhost")
MCP_PORT = os.getenv("MCP_PORT", "8008")

# Set the correct environment variables that FastMCP actually reads
os.environ["FASTMCP_PORT"] = MCP_PORT
os.environ["FASTMCP_HOST"] = MCP_HOST

mcp = FastMCP("Coles Product Search")

# Coles API configuration
COLES_API_BASE = "https://www.coles.com.au/api/bff/products"
DEFAULT_STORE_ID = "0584"  # Default store ID from the example

# Get API key from environment or use a placeholder
COLES_API_KEY = os.getenv("COLES_API_KEY", "YOUR_API_KEY_HERE")

def extract_unit_from_text(text: str) -> str:
    """Extract unit information from product text"""
    if not text:
        return ""
    
    text = text.lower()
    
    # Check for various units
    if re.search(r'\d+\s*kg\b', text):
        return "kg"
    elif re.search(r'\d+\s*g\b', text) and not re.search(r'\d+\s*mg\b', text):
        return "g"
    elif re.search(r'\d+\s*l\b', text) and not re.search(r'\d+\s*ml\b', text):
        return "L"
    elif re.search(r'\d+\s*ml\b', text):
        return "ml"
    elif "each" in text or "ea" in text:
        return "each"
    elif "pack" in text or "pk" in text:
        return "pack"
    
    return ""

@mcp.tool(description="Search for products at Coles")
def search_products(query: str, store_id: str = DEFAULT_STORE_ID, limit: int = 20, sort_by: str = "salesDescending") -> Dict[str, Any]:
    """
    Search for products using the Coles API.
    
    Args:
        query: The search term (e.g., "milk", "bread", "apples")
        store_id: The Coles store ID (default: 0584)
        limit: Maximum number of results (default: 20)
        sort_by: Sort order - "salesDescending", "priceAscending", "priceDescending" (default: salesDescending)
    
    Returns:
        Dictionary with search results
    """
    try:
        # Build the search URL
        search_url = f"{COLES_API_BASE}/search"
        
        # Set up the API request parameters
        params = {
            "storeId": store_id,
            "searchTerm": query,
            "start": "0",
            "sortBy": sort_by,
            "excludeAds": "true",
            "authenticated": "false",
            "subscription-key": COLES_API_KEY
        }
        
        # Use minimal headers that work!
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Make the API request
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 401:
            return {
                "success": False,
                "error": "API key is invalid or missing. Please set COLES_API_KEY environment variable.",
                "products": []
            }
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API returned status {response.status_code}: {response.text[:200]}",
                "products": []
            }
        
        # Parse the response
        data = response.json()
        
        # Extract products from the response
        products = []
        results = data.get("results", [])
        
        for item in results[:limit]:
            try:
                # Extract basic product info
                product = {
                    "id": item.get("id", ""),
                    "name": item.get("name", "Unknown"),
                    "brand": item.get("brand", ""),
                    "description": item.get("description", ""),
                }
                
                # Extract pricing information
                pricing = item.get("pricing", {})
                product["price"] = pricing.get("now")
                product["was_price"] = pricing.get("was")
                product["unit_price"] = pricing.get("unit", {}).get("price")
                product["unit_quantity"] = pricing.get("unit", {}).get("quantity")
                
                # Extract size/unit information
                product["size"] = item.get("size", "")
                product["package_size"] = item.get("packageSize", "")
                
                # Try to determine unit
                unit_text = f"{product['size']} {product['package_size']} {product['description']}"
                product["unit"] = extract_unit_from_text(unit_text)
                
                # Check if on special
                product["on_special"] = bool(product["was_price"] and product["price"] < product["was_price"])
                
                # Product URL
                product["url"] = f"https://www.coles.com.au/product/{product['id']}"
                
                products.append(product)
                
            except Exception as e:
                # Skip products that fail to parse
                continue
        
        return {
            "success": True,
            "query": query,
            "store_id": store_id,
            "count": len(products),
            "total_results": data.get("totalResultCount", len(products)),
            "products": products
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timed out",
            "products": []
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "products": []
        }

@mcp.tool(description="Get product details by ID")
def get_product_details(product_id: str, store_id: str = DEFAULT_STORE_ID) -> Dict[str, Any]:
    """
    Get detailed information about a specific product.
    
    Args:
        product_id: The Coles product ID
        store_id: The Coles store ID (default: 0584)
    
    Returns:
        Dictionary with product details
    """
    try:
        # Build the product URL
        product_url = f"{COLES_API_BASE}/{product_id}"
        
        # Set up parameters
        params = {
            "storeId": store_id,
            "subscription-key": COLES_API_KEY
        }
        
        # Use minimal headers that work!
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Make the API request
        response = requests.get(product_url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API returned status {response.status_code}",
                "product": None
            }
        
        # Parse the response
        product_data = response.json()
        
        return {
            "success": True,
            "product": product_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "product": None
        }

@mcp.tool(description="Find the cheapest option for a product")
def find_cheapest(product_name: str, store_id: str = DEFAULT_STORE_ID) -> Dict[str, Any]:
    """
    Find the cheapest option for a given product.
    
    Args:
        product_name: The product to search for
        store_id: The Coles store ID (default: 0584)
    
    Returns:
        Dictionary with the cheapest products sorted by unit price
    """
    # Search for the product
    results = search_products(product_name, store_id, limit=50, sort_by="priceAscending")
    
    if not results["success"] or not results["products"]:
        return results
    
    # Calculate unit prices for all products
    products_with_unit_price = []
    
    for product in results["products"]:
        # Skip if no price
        if not product.get("price"):
            continue
        
        # If unit price is already provided, use it
        if product.get("unit_price"):
            unit_price = product["unit_price"]
        else:
            # Try to calculate unit price from size
            unit_price = None
            size_text = f"{product.get('size', '')} {product.get('package_size', '')}"
            
            # Extract quantity from size
            quantity_match = re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|l|ml)', size_text.lower())
            if quantity_match:
                quantity = float(quantity_match.group(1))
                unit = quantity_match.group(2)
                
                # Convert to standard units for comparison
                if unit == 'g':
                    quantity = quantity / 1000  # Convert to kg
                    unit = 'kg'
                elif unit == 'ml':
                    quantity = quantity / 1000  # Convert to L
                    unit = 'L'
                
                if quantity > 0:
                    unit_price = product["price"] / quantity
        
        product["calculated_unit_price"] = unit_price
        products_with_unit_price.append(product)
    
    # Sort by unit price (cheapest first)
    products_with_unit_price.sort(key=lambda x: x.get("calculated_unit_price") or x.get("unit_price") or x.get("price", float('inf')))
    
    return {
        "success": True,
        "query": product_name,
        "count": len(products_with_unit_price),
        "products": products_with_unit_price[:10]  # Return top 10 cheapest
    }

@mcp.tool(description="Check Coles API status")
def check_api_status() -> Dict[str, Any]:
    """
    Check if the Coles API is accessible and the API key is valid.
    
    Returns:
        Dictionary with API status information
    """
    try:
        # Try a simple search
        result = search_products("test", limit=1)
        
        return {
            "api_accessible": result["success"],
            "api_key_configured": COLES_API_KEY != "YOUR_API_KEY_HERE",
            "api_key_valid": result["success"] and "401" not in result.get("error", ""),
            "store_id": DEFAULT_STORE_ID,
            "api_base_url": COLES_API_BASE,
            "details": result.get("error", "API is working") if not result["success"] else "API is working"
        }
    except Exception as e:
        return {
            "api_accessible": False,
            "api_key_configured": COLES_API_KEY != "YOUR_API_KEY_HERE",
            "api_key_valid": False,
            "error": str(e)
        }

if __name__ == "__main__":
    print("🛒 Coles Product Search MCP Server")
    print("=" * 50)
    
    # Check API key
    if COLES_API_KEY == "YOUR_API_KEY_HERE":
        print("⚠️  WARNING: No API key configured!")
        print("\nTo use this server, you need to:")
        print("1. Find the Coles API key (see instructions below)")
        print("2. Set it as an environment variable:")
        print("   export COLES_API_KEY='your-key-here'")
        print("\nOr create a .env file with:")
        print("   COLES_API_KEY=your-key-here")
    else:
        print(f"✓ API Key configured: {COLES_API_KEY[:10]}...")
    
    print(f"\nDefault Store ID: {DEFAULT_STORE_ID}")
    print(f"API Base URL: {COLES_API_BASE}")
    
    print("\n📝 Available tools:")
    print("  - search_products: Search for any product")
    print("  - get_product_details: Get detailed info about a product")
    print("  - find_cheapest: Find the best value options")
    print("  - check_api_status: Check if the API is working")
    
    print(f"\nServer will run at http://{MCP_HOST}:{MCP_PORT}/sse")
    print(f"(Using FASTMCP_PORT={MCP_PORT} environment variable)")
    
    # Run with SSE transport for Strands
    mcp.run(transport="sse")