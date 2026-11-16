const api = "http://localhost:8000/api/registration";

const start_form = document.querySelector("#start"), verify_form = document.querySelector("#verify"), complete_form = document.querySelector("#complete"), status_text = document.querySelector("#status");

let token = sessionStorage.getItem("registration_token"), verified = sessionStorage.getItem("registration_verified") === "yes";

function render() { start_form.hidden = !!token;
 verify_form.hidden = !token || verified;
 complete_form.hidden = !verified;
 }
async function request(path, data) { const response = await fetch(api + path, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
 const result = await response.json();
 if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Verifique os campos informados.");
 return result;
 }
function save(value, confirmed) { token=value;
 verified=confirmed;
 sessionStorage.setItem("registration_token",token);
 sessionStorage.setItem("registration_verified",confirmed?"yes":"no");
 render();
 }
function submit(form, callback) { form.addEventListener("submit",async event=>{event.preventDefault();
 const button=form.querySelector("button");
 button.disabled=true;
 status_text.textContent="";
 try { await callback(new FormData(form));
 } catch(error) { status_text.textContent=error.message;
 } finally { button.disabled=false;
 } });
 }
submit(start_form,async data=>{ const result=await request("/start",{email:data.get("email")});
save(result.token,false);
 });

submit(verify_form,async data=>{await request("/verify",{token,code:data.get("code")});
save(token,true);
});

complete_form.elements.type.addEventListener("change",()=>{document.querySelector("#card").hidden=complete_form.elements.type.value!=="credit_card";
});

submit(complete_form,async data=>{const payload=Object.fromEntries(data);
 payload.token=token;
 payload.plan_id=Number(payload.plan_id);
payload.phone=payload.phone||null;
payload.payment={type:payload.type};
if(payload.type==="credit_card") { for(const key of ["card_number","holder_name","cvc","expiration_month","expiration_year"])payload.payment[key]=key.startsWith("expiration_")?Number(payload[key]):payload[key];
 } for(const key of ["type","card_number","holder_name","cvc","expiration_month","expiration_year"])delete payload[key];
await request("/complete",payload);
sessionStorage.removeItem("registration_token");
sessionStorage.removeItem("registration_verified");
location.href="login.html";
});

document.querySelector("#restart").onclick=()=>{sessionStorage.removeItem("registration_token");
sessionStorage.removeItem("registration_verified");
location.reload();
};

fetch("http://localhost:8000/api/plans").then(r=>{if(!r.ok)throw new Error("Não foi possível carregar planos.");
return r.json();
}).then(plans=>{for(const plan of plans){const option=document.createElement("option");
option.value=plan.id;
option.textContent=`${plan.name} — R$ ${Number(plan.price).toFixed(2)}`;
complete_form.elements.plan_id.append(option);
}}).catch(e=>status_text.textContent=e.message);

fetch(api+"/config").then(r=>r.json()).then(config=>{if(!config.google_client_id)return;
const script=document.createElement("script");
script.src="https://accounts.google.com/gsi/client";
script.onload=()=>{google.accounts.id.initialize({client_id:config.google_client_id,callback:async response=>{try{const result=await request("/google",{credential:response.credential});
if(result.access_token){sessionStorage.setItem("quaseflix_token",result.access_token);
sessionStorage.setItem("quaseflix_account",JSON.stringify(result.account));
location.href="profiles.html";
}else{save(result.token,true);
}}catch(error){status_text.textContent=error.message;
}}});
google.accounts.id.renderButton(document.querySelector("#google"),{theme:"outline",size:"large"});
};
document.head.append(script);
});

render();
