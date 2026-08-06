
import URLs from "../url";

class AuthService {
  constructor() {

    this.baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"; 
    // this.baseUrl = "http://127.0.0.1:5000/"; // Direct Flask dev server
    this.headers =  { "Content-Type": "application/json" }
  }

  async login(requestObject) {
    let url = this.baseUrl + URLs.login;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      // The API is a different origin, and fetch defaults to
      // credentials: "same-origin" -- without this the browser silently
      // discards the session cookie the server sets here.
      credentials: "include",
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
      credentials: "include",
      body: JSON.stringify(requestObject),
    });
    const data = await response.json(); 
    return data
  }
}

export default new AuthService();
