// ── Auth ──────────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: 'buyer' | 'seller' | 'admin';
  is_active: boolean;
  avatar_url: string | null;
  created_at: string;
}

export interface UserPublic {
  id: string;
  full_name: string | null;
  avatar_url: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  role?: 'buyer' | 'seller';
}

// ── Categories ────────────────────────────────────────────────────────────────

export interface CategoryResponse {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image_url: string | null;
  parent_id: string | null;
  children?: CategoryResponse[];
}

// ── Products ──────────────────────────────────────────────────────────────────

export interface ProductListItem {
  id: string;
  title: string;
  slug: string;
  price: number;
  compare_at_price?: number | null;
  stock: number;
  status: 'draft' | 'active' | 'archived';
  images: string[];
  category_id: string | null;
  seller_id: string;
  average_rating: number;
  review_count: number;
  created_at: string;
}

export interface ProductResponse extends ProductListItem {
  description: string | null;
  tags: string[];
  category: CategoryResponse | null;
  seller: UserPublic;
}

export interface ProductCreate {
  title: string;
  description?: string;
  price: number;
  compare_at_price?: number;
  stock: number;
  category_id?: string;
  tags?: string[];
  sku?: string;
}

export interface ProductUpdate {
  title?: string;
  description?: string;
  price?: number;
  stock?: number;
  category_id?: string;
  status?: 'draft' | 'active' | 'archived';
}

export interface ProductFilters {
  q?: string;
  category_id?: string;
  min_price?: number;
  max_price?: number;
  min_rating?: number;
  page?: number;
  per_page?: number;
  sort?: string;
}

// ── Orders ────────────────────────────────────────────────────────────────────

export interface ShippingAddress {
  full_name?: string;
  phone?: string;
  line1: string;
  line2?: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
}

export interface OrderItemCreate {
  product_id: string;
  quantity: number;
}

export interface OrderCreate {
  items: OrderItemCreate[];
  shipping_address: ShippingAddress;
}

export interface OrderItemResponse {
  id: string;
  product_id: string | null;
  product_title: string;
  product_image: string | null;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

export type OrderStatus =
  | 'pending'
  | 'paid'
  | 'processing'
  | 'shipped'
  | 'delivered'
  | 'cancelled'
  | 'refunded';

export interface OrderResponse {
  id: string;
  buyer_id: string;
  buyer?: UserPublic;
  status: OrderStatus;
  items: OrderItemResponse[];
  subtotal: number;
  tax: number;
  shipping: number;
  total: number;
  shipping_address: ShippingAddress;
  razorpay_order_id: string | null;
  razorpay_payment_id: string | null;
  paid_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  created_at: string;
}

export interface CheckoutResponse {
  order_id: string;
  razorpay_order_id: string;
  amount_paise: number;
  currency: string;
  razorpay_key_id: string;
}

// ── Cart ──────────────────────────────────────────────────────────────────────

export interface CartItem {
  product_id: string;
  quantity: number;
  product: ProductListItem | null;
}

export interface CartResponse {
  items: CartItem[];
  subtotal: number;
  item_count: number;
}

// ── Reviews ───────────────────────────────────────────────────────────────────

export interface ReviewResponse {
  id: string;
  product_id: string;
  reviewer_id: string;
  reviewer?: UserPublic;
  rating: number;
  title: string | null;
  body: string | null;
  is_verified_purchase: boolean;
  helpful_count: number;
  created_at: string;
}

export interface RatingSummary {
  average: number;
  total: number;
  distribution: Record<string, number>;
}

export interface ReviewListResponse {
  reviews: PaginatedResponse<ReviewResponse>;
  rating_summary: RatingSummary;
}

export interface ReviewCreate {
  rating: number;
  title?: string;
  body?: string;
}

export interface ReviewUpdate {
  rating?: number;
  title?: string;
  body?: string;
}

// ── Common ────────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface MessageResponse {
  message: string;
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export interface AdminStats {
  total_users: number;
  total_sellers: number;
  total_buyers: number;
  total_products: number;
  active_products: number;
  total_orders: number;
  orders_by_status: Record<string, number>;
  revenue_this_month: number;
  revenue_last_month: number;
  new_users_this_week: number;
}
