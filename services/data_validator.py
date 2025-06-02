import re
from datetime import datetime
from typing import Dict, Any, List, Tuple
from decimal import Decimal, InvalidOperation

class InvoiceDataValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_invoice(self, invoice_data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """
        Validate and clean invoice data
        Returns: (cleaned_data, errors, warnings)
        """
        print(f"🔍 [Validator] Input: {invoice_data}")
        
        self.errors = []
        self.warnings = []
        
        cleaned_data = {}
        
        # First, flatten the nested LLM data structure
        flattened_data = self._flatten_llm_data(invoice_data)
        print(f"🔍 [Validator] Flattened: {flattened_data}")
        
        # Validate supplier information
        cleaned_data.update(self._validate_supplier_info(flattened_data))
        
        # Validate financial data
        cleaned_data.update(self._validate_financial_data(flattened_data))
        
        # Validate dates
        cleaned_data.update(self._validate_dates(flattened_data))
        
        # Validate contact information
        cleaned_data.update(self._validate_contact_info(flattened_data))
        
        # Cross-validate financial calculations
        self._cross_validate_amounts(cleaned_data)
        
        print(f"🔍 [Validator] Output: {cleaned_data}")
        print(f"🔍 [Validator] Errors: {self.errors}")
        print(f"🔍 [Validator] Warnings: {self.warnings}")
        
        return cleaned_data, self.errors, self.warnings
    
    def _flatten_llm_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert nested LLM schema to flat structure for validation"""
        flattened = {}
        
        # Handle nested supplier data
        supplier = data.get("supplier", {})
        if isinstance(supplier, dict):
            flattened["supplier_name"] = supplier.get("name")
            flattened["supplier_address"] = supplier.get("address") 
            flattened["supplier_email"] = supplier.get("email")
            flattened["supplier_phone_number"] = supplier.get("phone_number")
            flattened["supplier_vat_number"] = supplier.get("vat_number")
            flattened["supplier_website"] = supplier.get("website")
        
        # Map LLM field names to validator field names
        field_mapping = {
            "invoice_date": "expense_date",  # invoice_date -> expense_date
            "invoice_number": "invoice_number",
            "currency": "currency", 
            "total_net": "total_net",
            "total_tax": "total_tax",
            "total_amount_incl_tax": "total_amount",  # total_amount_incl_tax -> total_amount
            "total_amount": "total_amount"  # Also handle if already named total_amount
        }
        
        # Copy mapped fields
        for llm_field, validator_field in field_mapping.items():
            if llm_field in data:
                flattened[validator_field] = data[llm_field]
        
        # Copy any other fields directly
        for key, value in data.items():
            if key not in ["supplier"] and key not in field_mapping:
                flattened[key] = value
        
        return flattened
    
    def _validate_supplier_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate supplier information"""
        result = {}
        
        # Supplier name
        supplier_name = self._clean_string(data.get("supplier_name"))
        if supplier_name:
            if len(supplier_name) > 255:
                self.warnings.append("Supplier name truncated to 255 characters")
                supplier_name = supplier_name[:255]
            result["supplier_name"] = supplier_name
        else:
            self.errors.append("Supplier name is required")
        
        # VAT number validation
        vat_number = self._clean_string(data.get("supplier_vat_number"))
        if vat_number:
            cleaned_vat = self._validate_vat_number(vat_number)
            if cleaned_vat:
                result["supplier_vat_number"] = cleaned_vat
            else:
                self.warnings.append(f"Invalid VAT number format: {vat_number}")
        
        # Address
        address = self._clean_string(data.get("supplier_address"))
        if address:
            result["supplier_address"] = address
        
        # Website
        website = self._clean_string(data.get("supplier_website"))
        if website:
            cleaned_website = self._validate_website(website)
            if cleaned_website:
                result["supplier_website"] = cleaned_website
            else:
                self.warnings.append(f"Invalid website format: {website}")
        
        return result
    
    def _validate_financial_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate financial amounts"""
        result = {}
        
        # Currency
        currency = self._clean_string(data.get("currency"))
        if currency:
            currency = currency.upper()
            if len(currency) > 10:
                self.warnings.append("Currency code truncated")
                currency = currency[:10]
            result["currency"] = currency
        else:
            # Default currency if not provided
            result["currency"] = "USD"
            self.warnings.append("Currency not provided, defaulting to USD")
        
        # Validate amounts
        amounts = ["total_net", "total_tax", "total_amount"]
        for amount_field in amounts:
            amount = self._validate_amount(data.get(amount_field))
            if amount is not None:
                result[amount_field] = float(amount)
            elif data.get(amount_field) is not None:
                self.warnings.append(f"Invalid {amount_field}: {data.get(amount_field)}")
        
        return result
    
    def _validate_dates(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate date fields"""
        result = {}
        
        expense_date = data.get("expense_date")
        if expense_date:
            parsed_date = self._parse_date(expense_date)
            if parsed_date:
                # Check if date is reasonable (not too far in past/future)
                now = datetime.now()
                years_diff = abs((now - parsed_date).days / 365.25)
                
                if years_diff > 10:
                    self.warnings.append(f"Expense date seems unusual: {parsed_date.date()}")
                
                result["expense_date"] = parsed_date
            else:
                self.warnings.append(f"Invalid expense date format: {expense_date}")
        
        return result
    
    def _validate_contact_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contact information"""
        result = {}
        
        # Email validation
        email = self._clean_string(data.get("supplier_email"))
        if email:
            if self._validate_email(email):
                result["supplier_email"] = email.lower()
            else:
                self.warnings.append(f"Invalid email format: {email}")
        
        # Phone validation
        phone = self._clean_string(data.get("supplier_phone_number"))
        if phone:
            cleaned_phone = self._validate_phone(phone)
            if cleaned_phone:
                result["supplier_phone_number"] = cleaned_phone
            else:
                self.warnings.append(f"Invalid phone format: {phone}")
        
        # Invoice number
        invoice_number = self._clean_string(data.get("invoice_number"))
        if invoice_number:
            if len(invoice_number) > 100:
                self.warnings.append("Invoice number truncated")
                invoice_number = invoice_number[:100]
            result["invoice_number"] = invoice_number
        else:
            self.warnings.append("Invoice number is missing")
        
        return result
    
    def _cross_validate_amounts(self, data: Dict[str, Any]):
        """Cross-validate financial calculations"""
        net = data.get("total_net")
        tax = data.get("total_tax")
        total = data.get("total_amount")
        
        if net is not None and tax is not None and total is not None:
            calculated_total = net + tax
            difference = abs(calculated_total - total)
            
            # Allow small rounding differences (0.02)
            if difference > 0.02:
                self.warnings.append(
                    f"Amount calculation mismatch: {net} + {tax} = {calculated_total}, "
                    f"but total_amount is {total} (difference: {difference})"
                )
        
        # Check for negative amounts
        for field in ["total_net", "total_tax", "total_amount"]:
            amount = data.get(field)
            if amount is not None and amount < 0:
                self.warnings.append(f"Negative amount detected in {field}: {amount}")
    
    def _clean_string(self, value) -> str:
        """Clean and normalize string values"""
        if not value:
            return None
        
        if isinstance(value, str):
            # Remove extra whitespace and normalize
            cleaned = ' '.join(value.strip().split())
            return cleaned if cleaned else None
        
        return str(value).strip() or None
    
    def _validate_amount(self, value) -> Decimal:
        """Validate and parse monetary amounts"""
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError):
                return None
        
        if isinstance(value, str):
            # Remove currency symbols and clean up
            cleaned = re.sub(r'[€$£¥₹,\s]', '', value.strip())
            try:
                return Decimal(cleaned)
            except (InvalidOperation, ValueError):
                return None
        
        return None
    
    def _parse_date(self, date_str) -> datetime:
        """Parse various date formats"""
        if not date_str:
            return None
        
        if isinstance(date_str, datetime):
            return date_str
        
        formats = [
            "%d/%m/%Y",  # DD/MM/YYYY (LLM format) - put this first!
            "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y",
            "%Y/%m/%d", "%B %d, %Y", "%d %B %Y", "%d.%m.%Y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str(date_str).strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_phone(self, phone: str) -> str:
        """Validate and clean phone number"""
        if not phone:
            return None
            
        # Remove all non-digit characters except + at the beginning
        cleaned = re.sub(r'[^\d+]', '', phone)
        if cleaned.startswith('+'):
            cleaned = '+' + re.sub(r'[^\d]', '', cleaned[1:])
        else:
            cleaned = re.sub(r'[^\d]', '', cleaned)
        
        # Check if it's a reasonable length (7-15 digits)
        digit_count = len(re.sub(r'[^\d]', '', cleaned))
        if 7 <= digit_count <= 15:
            return cleaned
        
        return None
    
    def _validate_vat_number(self, vat: str) -> str:
        """Basic VAT number validation"""
        if not vat:
            return None
            
        # Remove spaces and convert to uppercase
        cleaned = re.sub(r'\s+', '', vat.upper())
        
        # Basic format check (2 letters + 8-12 digits for EU VAT)
        if re.match(r'^[A-Z]{2}[\dA-Z]{8,12}$', cleaned):
            return cleaned
        
        # Or just numbers (some countries)
        if re.match(r'^\d{8,12}$', cleaned):
            return cleaned
        
        return None
    
    def _validate_website(self, website: str) -> str:
        """Validate and clean website URL"""
        if not website:
            return None
            
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        
        # Basic URL pattern
        pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/?.*$'
        if re.match(pattern, website):
            return website
        
        return None