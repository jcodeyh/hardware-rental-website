
import URLs from "../url";

class AuthService {
  constructor() {
<<<<<<< HEAD
    // Vite inlines VITE_* at build time; falls back to the local Flask
    // server so `npm run dev` keeps working with no extra setup.
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    this.headers = { "Content-Type": "application/json" };
=======
    // this.baseUrl = "http://127.0.0.1:5000/";
    this.baseUrl = "http://127.0.0.1:8000/"; // Docker Compose exposes the backend on port 8000
    this.headers =  { "Content-Type": "application/json" }
>>>>>>> main
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
