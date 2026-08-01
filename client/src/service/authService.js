
import URLs from "../url";

class AuthService {
  constructor() {
    // this.baseUrl = "http://127.0.0.1:5000/";
    this.baseUrl = "http://127.0.0.1:8000/"; // Docker Compose exposes the backend on port 8000
    this.headers =  { "Content-Type": "application/json" }
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
