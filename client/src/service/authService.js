
import URLs from "../url";

class AuthService {
  constructor() {
    // Vite inlines VITE_* at build time; falls back to the local Flask
    // server so `npm run dev` keeps working with no extra setup.
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    this.headers = { "Content-Type": "application/json" };
  }

  async login(requestObject) {
    let url = this.baseUrl + URLs.login;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(requestObject),
    });
    const data = await response.json();
    return data
  }

  async signup(requestObject) {
    let url = this.baseUrl + URLs.signUp;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(requestObject),
    });
    const data = await response.json(); 
    return data
  }
}

export default new AuthService();
