import { Link } from 'react-router-dom'
import { Store } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200 mt-auto">
      <div className="max-w-7xl mx-auto px-4 py-10">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <Link to="/" className="flex items-center gap-2 text-indigo-600 font-bold text-lg mb-3">
              <Store size={20} />
              Marketplace
            </Link>
            <p className="text-gray-500 text-sm">
              India's trusted multi-category marketplace. Buy and sell with confidence.
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-3">Shop</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li><Link to="/" className="hover:text-indigo-600">All Products</Link></li>
              <li><Link to="/cart" className="hover:text-indigo-600">Cart</Link></li>
              <li><Link to="/orders" className="hover:text-indigo-600">My Orders</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-3">Sell</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li><Link to="/seller/products" className="hover:text-indigo-600">My Products</Link></li>
              <li><Link to="/seller/products/new" className="hover:text-indigo-600">Add Product</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-3">Account</h4>
            <ul className="space-y-2 text-sm text-gray-600">
              <li><Link to="/profile" className="hover:text-indigo-600">Profile</Link></li>
              <li><Link to="/login" className="hover:text-indigo-600">Login</Link></li>
              <li><Link to="/register" className="hover:text-indigo-600">Register</Link></li>
            </ul>
          </div>
        </div>

        <div className="mt-8 pt-6 border-t border-gray-200 text-center text-sm text-gray-400">
          &copy; {new Date().getFullYear()} Marketplace. All rights reserved. Prices in INR (₹).
        </div>
      </div>
    </footer>
  )
}
