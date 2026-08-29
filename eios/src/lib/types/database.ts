/**
 * Supabase Database Types — Auto-generated via `npm run db:types`
 * This is the initial stub. Run the command after applying migrations.
 */

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Database {
  public: {
    Tables: {
      organizations: {
        Row: {
          id: string;
          name: string;
          type: "family_office" | "holding" | "trust" | "foundation";
          jurisdiction: string | null;
          tax_id: string | null;
          metadata: Json | null;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["organizations"]["Row"],
          "id" | "created_at" | "updated_at"
        >;
        Update: Partial<
          Database["public"]["Tables"]["organizations"]["Insert"]
        >;
      };
      profiles: {
        Row: {
          id: string;
          user_id: string;
          organization_id: string;
          role: "owner" | "advisor" | "viewer" | "admin";
          full_name: string;
          email: string;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["profiles"]["Row"],
          "id" | "created_at" | "updated_at"
        >;
        Update: Partial<Database["public"]["Tables"]["profiles"]["Insert"]>;
      };
      entities: {
        Row: {
          id: string;
          organization_id: string;
          name: string;
          type: "natural_person" | "company" | "trust" | "fund" | "spv";
          jurisdiction: string;
          tax_id: string | null;
          incorporation_date: string | null;
          metadata: Json | null;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["entities"]["Row"],
          "id" | "created_at" | "updated_at"
        >;
        Update: Partial<Database["public"]["Tables"]["entities"]["Insert"]>;
      };
      portfolios: {
        Row: {
          id: string;
          organization_id: string;
          entity_id: string;
          name: string;
          currency: string;
          custodian: string | null;
          account_number: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["portfolios"]["Row"],
          "id" | "created_at" | "updated_at"
        >;
        Update: Partial<Database["public"]["Tables"]["portfolios"]["Insert"]>;
      };
      positions: {
        Row: {
          id: string;
          portfolio_id: string;
          asset_type:
            | "equity"
            | "fixed_income"
            | "fund"
            | "real_estate"
            | "private_equity"
            | "cash"
            | "derivative"
            | "crypto";
          symbol: string | null;
          isin: string | null;
          name: string;
          quantity: number;
          cost_basis: number;
          cost_basis_currency: string;
          current_price: number | null;
          current_value: number | null;
          unrealized_pnl: number | null;
          metadata: Json | null;
          as_of_date: string;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["positions"]["Row"],
          "id" | "created_at" | "updated_at"
        >;
        Update: Partial<Database["public"]["Tables"]["positions"]["Insert"]>;
      };
      transactions: {
        Row: {
          id: string;
          portfolio_id: string;
          position_id: string | null;
          type: "buy" | "sell" | "dividend" | "coupon" | "fee" | "transfer";
          quantity: number | null;
          price: number | null;
          amount: number;
          currency: string;
          executed_at: string;
          settlement_date: string | null;
          notes: string | null;
          metadata: Json | null;
          created_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["transactions"]["Row"],
          "id" | "created_at"
        >;
        Update: Partial<
          Database["public"]["Tables"]["transactions"]["Insert"]
        >;
      };
      decisions: {
        Row: {
          id: string;
          organization_id: string;
          title: string;
          status: "draft" | "analysis" | "review" | "approved" | "rejected" | "executed";
          decision_type: "investment" | "fiscal" | "corporate" | "risk";
          summary: string | null;
          analysis: Json | null;
          risk_assessment: Json | null;
          fiscal_impact: Json | null;
          approved_by: string | null;
          approved_at: string | null;
          created_by: string;
          created_at: string;
          updated_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["decisions"]["Row"],
          "id" | "created_at" | "updated_at"
        >;
        Update: Partial<Database["public"]["Tables"]["decisions"]["Insert"]>;
      };
      documents: {
        Row: {
          id: string;
          organization_id: string;
          entity_id: string | null;
          title: string;
          file_path: string;
          mime_type: string;
          size_bytes: number;
          doc_type: string | null;
          extracted_text: string | null;
          embedding: number[] | null;
          metadata: Json | null;
          uploaded_by: string;
          created_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["documents"]["Row"],
          "id" | "created_at"
        >;
        Update: Partial<Database["public"]["Tables"]["documents"]["Insert"]>;
      };
      audit_log: {
        Row: {
          id: string;
          organization_id: string;
          user_id: string;
          action: string;
          resource_type: string;
          resource_id: string;
          details: Json | null;
          ip_address: string | null;
          created_at: string;
        };
        Insert: Omit<
          Database["public"]["Tables"]["audit_log"]["Row"],
          "id" | "created_at"
        >;
        Update: never;
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: {
      org_type: "family_office" | "holding" | "trust" | "foundation";
      user_role: "owner" | "advisor" | "viewer" | "admin";
      entity_type: "natural_person" | "company" | "trust" | "fund" | "spv";
      asset_type:
        | "equity"
        | "fixed_income"
        | "fund"
        | "real_estate"
        | "private_equity"
        | "cash"
        | "derivative"
        | "crypto";
      tx_type: "buy" | "sell" | "dividend" | "coupon" | "fee" | "transfer";
      decision_status:
        | "draft"
        | "analysis"
        | "review"
        | "approved"
        | "rejected"
        | "executed";
      decision_type: "investment" | "fiscal" | "corporate" | "risk";
    };
  };
}

export type Tables<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T]["Row"];
export type InsertTables<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T]["Insert"];
export type UpdateTables<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T]["Update"];
