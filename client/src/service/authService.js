
import URLs from "../url";

class AuthService {
  constructor() {
    this.baseUrl = "http://localhost:8000";
    this.headers =  { "Content-Type": "application/json" }
  }

  async login(requestObject) {
    let url = this.baseUrl + URLs.login;
    let response = await fetch(url, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(requestObject),
    });
    return response
  }
}

export default new AuthService();
