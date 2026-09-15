"""
RealEstate-QBO-Sync: Automated Workflow & QuickBooks Online API Integration
Author: Wendy Liliana Martínez Ángeles
Purpose: Ingests real estate deal events, calculates commissions, 
         and generates Customer & Invoice records in QBO Sandbox via REST API.
"""

import json
import uuid
import requests

# ==============================================================================
# CONFIGURACIÓN Y CREDENCIALES (INTUIT QBO SANDBOX)
# ==============================================================================
# Si tienes tu token del OAuth Playground, pon SANDBOX_MOCK_MODE = False
SANDBOX_MOCK_MODE = True  

QBO_REALM_ID = "TU_REALM_ID_AQUI"
QBO_ACCESS_TOKEN = "TU_BEARER_TOKEN_AQUI"
QBO_BASE_URL = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{QBO_REALM_ID}"

HEADERS = {
    "Authorization": f"Bearer {QBO_ACCESS_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}


# ==============================================================================
# 1. MOTOR DE LÓGICA DE NEGOCIO (WORKFLOW ENGINE)
# ==============================================================================
def process_real_estate_deal(deal_event: dict) -> dict:
    """
    Valida el evento del trato inmobiliario y calcula la estructura de comisiones.
    """
    property_val = deal_event.get("property_value", 0.0)
    agent_tier = deal_event.get("agent_tier", "Standard")

    # Regla de comisión: 3.0% base, 2.5% para propiedades mayores a 1M USD
    commission_rate = 0.025 if property_val >= 1_000_000 or agent_tier == "TopProducer" else 0.030
    commission_amount = round(property_val * commission_rate, 2)
    brokerage_fee = round(commission_amount * 0.10, 2)  # Retención operativa de Fusion Growth (10%)
    agent_net_payout = round(commission_amount - brokerage_fee, 2)

    return {
        "client_name": deal_event["client_name"],
        "client_email": deal_event["client_email"],
        "deal_id": deal_event.get("deal_id", f"DL-{uuid.uuid4().hex[:6].upper()}"),
        "property_value": property_val,
        "commission_amount": commission_amount,
        "brokerage_fee": brokerage_fee,
        "agent_net_payout": agent_net_payout
    }


# ==============================================================================
# 2. INTEGRACIÓN CON QUICKBOOKS ONLINE API
# ==============================================================================
class QBOIntegrationService:
    def __init__(self, base_url: str, headers: dict, mock_mode: bool = False):
        self.base_url = base_url
        self.headers = headers
        self.mock_mode = mock_mode

    def create_customer(self, name: str, email: str) -> str:
        """Crea un cliente en QBO si no existe y devuelve su Id numérico."""
        payload = {
            "DisplayName": f"{name} ({uuid.uuid4().hex[:4]})",  # Sufijo único requerido por QBO
            "PrimaryEmailAddr": {"Address": email},
            "Notes": "Cliente incorporado vía pipeline automatizado de integración."
        }

        if self.mock_mode:
            mock_id = "58"
            print(f"[MOCK QBO API] Cliente creado: '{name}' con Id: {mock_id}")
            return mock_id

        endpoint = f"{self.base_url}/customer"
        res = requests.post(endpoint, json=payload, headers=self.headers)
        if res.status_code in (200, 201):
            customer_id = res.json()["Customer"]["Id"]
            print(f"✅ [QBO API] Cliente creado en Sandbox exitosamente. Id: {customer_id}")
            return customer_id
        else:
            raise RuntimeError(f"Fallo al crear Customer en QBO ({res.status_code}): {res.text}")

    def create_commission_invoice(self, customer_id: str, deal_data: dict) -> dict:
        """Genera una factura (Invoice) en QBO vinculada al cliente creado."""
        payload = {
            "CustomerRef": {"value": customer_id},
            "CustomerMemo": {
                "value": f"Deal Ref: {deal_data['deal_id']} - Retención operativa: ${deal_data['brokerage_fee']}"
            },
            "Line": [
                {
                    "Amount": deal_data["commission_amount"],
                    "DetailType": "SalesItemLineDetail",
                    "Description": f"Comisión de corretaje por propiedad de ${deal_data['property_value']:,.2f}",
                    "SalesItemLineDetail": {
                        "ItemRef": {"value": "1", "name": "Services"},  # Item 'Services' por defecto en Sandbox
                        "UnitPrice": deal_data["commission_amount"],
                        "Qty": 1
                    }
                }
            ]
        }

        if self.mock_mode:
            mock_invoice = {
                "InvoiceId": "9021",
                "TotalAmt": deal_data["commission_amount"],
                "DocNumber": f"INV-{deal_data['deal_id']}",
                "Status": "Created (Mock)"
            }
            print(f"[MOCK QBO API] Factura emitida: DocNum {mock_invoice['DocNumber']} por ${mock_invoice['TotalAmt']}")
            return mock_invoice

        endpoint = f"{self.base_url}/invoice"
        res = requests.post(endpoint, json=payload, headers=self.headers)
        if res.status_code in (200, 201):
            inv = res.json()["Invoice"]
            print(f"🎉 [QBO API] Factura #{inv.get('DocNumber', inv['Id'])} creada por ${inv['TotalAmt']} USD")
            return {"InvoiceId": inv["Id"], "TotalAmt": inv["TotalAmt"], "DocNumber": inv.get("DocNumber")}
        else:
            raise RuntimeError(f"Fallo al crear Invoice en QBO ({res.status_code}): {res.text}")


# ==============================================================================
# 3. DISPARADOR DEL PIPELINE (EJECUCIÓN)
# ==============================================================================
if __name__ == "__main__":
    # Evento de prueba: Un agente de bienes raíces cierra una propiedad
    incoming_deal_event = {
        "deal_id": "DEAL-TX-8829",
        "client_name": "Valeria Morales",
        "client_email": "valeria.morales@example.com",
        "property_value": 750000.0,
        "agent_tier": "Standard"
    }

    print("--- INICIANDO WORKFLOW DE INTEGRACIÓN INMOBILIARIA ---")
    
    # 1. Proceso analítico y validación
    processed_deal = process_real_estate_deal(incoming_deal_event)
    print(f"• Trato Validado: {processed_deal['deal_id']}")
    print(f"• Valor Propiedad: ${processed_deal['property_value']:,.2f}")
    print(f"• Comisión Total (3%): ${processed_deal['commission_amount']:,.2f}")
    print(f"• Pago Neto a Agente: ${processed_deal['agent_net_payout']:,.2f}")

    # 2. Invocación de QuickBooks Online API
    qbo_service = QBOIntegrationService(QBO_BASE_URL, HEADERS, mock_mode=SANDBOX_MOCK_MODE)
    
    # Alta de cliente y factura
    customer_id = qbo_service.create_customer(processed_deal["client_name"], processed_deal["client_email"])
    invoice_result = qbo_service.create_commission_invoice(customer_id, processed_deal)

    print("\n--- WORKFLOW FINALIZADO CON ÉXITO ---")
    print(f"Resultado final: {json.dumps(invoice_result, indent=2)}")