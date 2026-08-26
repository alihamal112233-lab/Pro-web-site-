const API = window.location.origin;

// ট্যাব সুইচিং (লগইন / রেজিস্টার)
function switchTab(tab, btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    btn.classList.add('active');
    document.getElementById(tab + '-tab').classList.add('active');
}

// লগইন হ্যান্ডলার
async function handleLogin() {
    const user = document.getElementById('loginUser').value.trim();
    const pass = document.getElementById('loginPass').value.trim();
    const msg = document.getElementById('loginMsg');
    const btn = document.getElementById('loginBtn');

    if (!user || !pass) {
        msg.textContent = "সব ফিল্ড পূরণ করুন!";
        return;
    }

    btn.disabled = true;
    btn.textContent = "লগইন হচ্ছে...";
    msg.textContent = "";

    try {
        const res = await fetch(API + '/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });

        const data = await res.json();

        if (res.ok) {
            localStorage.setItem('token', data.token);
            localStorage.setItem('role', data.role);
            msg.style.color = "#00897B";
            msg.textContent = "লগইন সফল! রিডাইরেক্ট হচ্ছে...";
            
            setTimeout(() => {
                if (data.role === 'admin') {
                    window.location.href = '/admin';
                } else {
                    window.location.href = '/';
                }
            }, 1000);
        } else {
            msg.style.color = "#E11D48";
            msg.textContent = data.detail || "লগইন ব্যর্থ হয়েছে!";
            btn.disabled = false;
            btn.textContent = "লগইন করুন";
        }
    } catch (e) {
        msg.style.color = "#E11D48";
        msg.textContent = "সার্ভার এরর!";
        btn.disabled = false;
        btn.textContent = "লগইন করুন";
    }
}

// রেজিস্ট্রেশন হ্যান্ডলার
async function handleFinalRegister() {
    const username = document.getElementById('regUsername').value.trim();
    const mobile = document.getElementById('regMobile').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const pass = document.getElementById('regPass').value.trim();
    const dist = document.getElementById('regDistrict').value;
    const upazila = document.getElementById('regUpazila').value;
    const msg = document.getElementById('regMsg');
    const btn = document.getElementById('regBtn');

    if (!username || !pass) {
        msg.textContent = "ইউজারনেম এবং পাসওয়ার্ড বাধ্যতামূলক!";
        return;
    }

    btn.disabled = true;
    btn.textContent = "একাউন্ট তৈরি হচ্ছে...";
    msg.textContent = "";

    try {
        const res = await fetch(API + '/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: username,
                password: pass,
                email: email,
                mobile: mobile,
                district: dist,
                upazila: upazila
            })
        });

        const data = await res.json();

        if (res.ok) {
            localStorage.setItem('token', data.token);
            localStorage.setItem('role', 'user');
            msg.style.color = "#00897B";
            msg.textContent = "রেজিস্ট্রেশন সফল! ১৫ ৳ বোনাস যোগ হয়েছে...";
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        } else {
            msg.style.color = "#E11D48";
            msg.textContent = data.detail || "রেজিস্ট্রেশন ব্যর্থ হয়েছে!";
            btn.disabled = false;
            btn.textContent = "নিশ্চিত রেজিস্ট্রেশন করুন";
        }
    } catch (e) {
        msg.style.color = "#E11D48";
        msg.textContent = "সার্ভার সমস্যা!";
        btn.disabled = false;
        btn.textContent = "নিশ্চিত রেজিস্ট্রেশন করুন";
    }
}

// জেলা ও উপজেলা তালিকা লোড করা
const distList = ["ঢাকা", "চট্টগ্রাম", "টাঙ্গাইল", "পটুয়াখালী", "নওগাঁ"];
const upzMap = {
    "ঢাকা": ["ধানমন্ডি", "গুলশান", "মিরপুর", "মতিঝিল"],
    "চট্টগ্রাম": ["পটিয়া", "সীতাকুণ্ড", "রাউজান"],
    "টাঙ্গাইল": ["মধুপুর", "ঘাটাইল", "কালিহাতী"],
    "পটুয়াখালী": ["বাউফল", "গলাচিপা"],
    "নওগাঁ": ["পত্নীতলা", "ধামইরহাট"]
};

window.onload = function() {
    const dSel = document.getElementById('regDistrict');
    const uSel = document.getElementById('regUpazila');
    if (dSel) {
        distList.forEach(d => {
            dSel.innerHTML += `<option value="${d}">${d}</option>`;
        });
        dSel.onchange = function() {
            uSel.innerHTML = '<option value="">-- উপজেলা সিলেক্ট করুন --</option>';
            const upzs = upzMap[dSel.value] || [];
            upzs.forEach(u => {
                uSel.innerHTML += `<option value="${u}">${u}</option>`;
            });
        };
    }
};
