from langchain_community.tools.tavily_search import TavilySearchResults



import http.client
import json
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from langchain.tools import tool


class PropertySearchFields(BaseModel):
    city: Optional[List[str]] = Field(
        None,
        description="List of Cities to search properties (e.g., ['Houston', 'Dallas']), CAN NEVER BE A NUMBER",
    )
    community: Optional[List[str]] = Field(
        None,
        description="List of Communities to search properties on. {Key Communities: cinco ranch, copperfield, eaglewood, canyon gate at brazon, clear lake city}",
    )
    zip_code: Optional[str] = Field(
        None,
        description="Numeric Zip code to search properties by, (e.g., 77027, 77024). Zip codes usually start with '77'.",
    )
    bedrooms: Optional[Dict[str, int]] = Field(
        None,
        description="Dictionary with Number of Bedrooms with keys 'min', 'max', or 'equal'",
    )
    baths: Optional[Dict[str, int]] = Field(
        None,
        description="Dictionary with Number of Bathrooms with keys 'min', 'max', or 'equal'",
    )
    price: Optional[Dict[str, int]] = Field(
        None,
        description="Dictionary with Price of property with keys 'min', 'max', or 'equal'",
    )
    for_sale: Optional[int] = Field(
        1, description="Indicates if the property is on rent"
    )

class PropertySearchResultItem(BaseModel):
    mlsnum: Optional[str]
    address: Optional[str]
    price: Optional[float]
    beds: int
    baths: int
    city: str
    zipCode: str
    sqft: int
#args_schema=PropertySearchFields
class PropertySearchInput(BaseModel):
    fields: PropertySearchFields = Field(
        ..., description="Input fields to search properties"
    )
@tool(args_schema=PropertySearchInput)
def search_properties(fields: PropertySearchFields) ->Dict:
    """Search properties based on input filters."""
    # Implement your API connection and handling here
    # Dummy data for the sake of example
    print("1")
    properties = [
        {"property":
        # PropertySearchResultItem(
          """  mlsnum="123456",
            address="123 Main St",
            price=350000.0,
            beds=3,
            baths=2,
            city="Houston",
            zipCode="77002",
            sqft=1500   """} 
            # )
    ]
    return properties

# Example use:
# Create an instance of PropertySearchFields with the desired search criteria
# search_criteria = PropertySearchFields(city=["Houston"], max_price=500000)
# properties = search_properties(fields=search_criteria)
tools = [search_properties]