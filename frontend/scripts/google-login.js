fetch("http://localhost:8000/api/registration/config").then(r=>r.json()).then(config=>{
 if(!config.google_client_id)return;

 const script=document.createElement("script");
script.src="https://accounts.google.com/gsi/client";

 script.onload=()=>{google.accounts.id.initialize({client_id:config.google_client_id,callback:async response=>{const result=await fetch("http://localhost:8000/api/registration/google",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({credential:response.credential})});
const data=await result.json();
if(!result.ok){const error=document.querySelector("#login-error");
error.hidden=false;
error.textContent=data.detail;
return;
}if(data.access_token){QuaseflixSession.save(data.access_token,data.account);
location.href="profiles.html";
}else{sessionStorage.setItem("registration_token",data.token);
sessionStorage.setItem("registration_verified","yes");
location.href="register.html";
}}});
google.accounts.id.renderButton(document.querySelector("#google-login"),{theme:"outline",size:"large"});
};
document.head.append(script);

}).catch(()=>{});
