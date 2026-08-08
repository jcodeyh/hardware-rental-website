import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { toast } from "react-toastify";
import AuthService from '../service/authService.js';
export default function Signup() {
  const [userName, setUserName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const navigate = useNavigate();
  async function handleSubmit(e) {
    e.preventDefault();

     e.preventDefault();
        let requestObject = {
          "username" : userName,
          "password" :password,
        }
        try{
          let response = await AuthService.signup(requestObject)
         
          if(response && response.user_id){
            console.log("Sign-Up  successful")
            toast.success("Sign-Up  successful")
            navigate('/login')
          }
          else if(response && response.error){
             toast.error(response.error)
          }
          else {
            toast.error("signup failed with some other status-code")
          }
        }
        catch (error) {

      }
  }

  function clearForm (){
    e.preventDefault();
    setUserName('')
    setPassword('')
    setConfirmPassword('')
  }

  return (
    <div className='page'>
      <div className="container">
      <h1>Sign Up</h1>
      <form className='mt-4'>
        <div>
          <label htmlFor="userName">User Name</label>
          <input id="userName" value={userName}  onChange={(e) => setUserName(e.target.value)}/>
        </div>

        <div>
          <label htmlFor="password">Password</label>
          <input id="password" type="password" value={password}  onChange={(e) => setPassword(e.target.value)}/>
        </div>

         <div>
          <label htmlFor="confirmPassword">Confirm Password</label>
          <input id="confirmPassword" type="password" value={confirmPassword}  onChange={(e) => setConfirmPassword(e.target.value)}/>
        </div>

        <div className="row">
          <div className="col-lg-12 full-width">
            <div className="row">
              <div className="col-lg-6">
                <button className='secondary' onClick={clearForm}>Clear</button>
              </div>

              <div className="col-lg-6">
                <button  className={`${((userName == "") || (password == "") || (confirmPassword == "") || (password != confirmPassword) ) ? 'btn-disabled' : 'button'}`}
                disabled={((userName == "") || (password == "") || (confirmPassword == "") || (password != confirmPassword) )? true : false  } onClick={handleSubmit}>Sign Up</button>
              </div>
            </div>
          </div>
        </div>
      </form>
       <div className='signUpLink mt-4'>Already have an account? <Link to="/login">Login</Link></div>

    </div>
    </div>
  )
}
