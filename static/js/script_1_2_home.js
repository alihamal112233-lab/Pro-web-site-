const API = window.location.origin;
let currentUser = null;

// পেজ লোড হওয়ার সাথে সাথে ইউজারের ব্যালেন্স ও লগইন চেক
async function checkAuth() {
    const token = localStorage.getItem('token');
    const authLinks = document.getElementById('authLinks');
    const userLinks = document.getElementById('userLinks');
    const adminLink = document.getElementById('adminLink');

    if (!token) {
        if (authLinks) authLinks.style.display = 'flex';
        if (userLinks) userLinks.style.display = 'none';
        return;
    }

    try {
        const res = await fetch(API + '/api/user/me', {
            headers: { 'Authorization': 'Bearer ' + token }
        });

        if (res.ok) {
            currentUser = await res.json();
            if (authLinks) authLinks.style.display = 'none';
            if (userLinks) userLinks.style.display = 'block';

            const firstLetter = currentUser.username.charAt(0).toUpperCase();
            document.getElementById('userAvatar').textContent = firstLetter;
            document.getElementById('sidebarAvatar').textContent = firstLetter;
            document.getElementById('sidebarName').textContent = currentUser.username;
            document.getElementById('sidebarUid').textContent = currentUser.uid;
            document.getElementById('sidebarBal').textContent = currentUser.balance;

            if (currentUser.role === 'admin' && adminLink) {
                adminLink.style.display = 'inline-block';
            }
        } else {
            localStorage.clear();
            if (authLinks) authLinks.style.display = 'flex';
            if (userLinks) userLinks.style.display = 'none';
        }
    } catch (e) {
        console.error("Auth check failed:", e);
    }
}

// সার্চ ফাংশন (ব্যালেন্স কেটে কার্ড রেজাল্ট দেখানো)
async function searchVoter() {
    const token = localStorage.getItem('token');
    if (!token) {
        showToast("অনুসন্ধান করতে প্রথমে লগইন করুন!");
        setTimeout(() => window.location.href = '/login', 1200);
        return;
    }

    const dist = document.getElementById('district').value;
    const upz = document.getElementById('upazila').value;
    const name = document.getElementById('voterName').value.trim();
    const father = document.getElementById('fatherName').value.trim();
    const mother = document.getElementById('motherName').value.trim();
    const dob = document.getElementById('dob').value.trim();
    const btn = document.getElementById('searchBtn');
    const rBody = document.getElementById('resultBody');
    const rCount = document.getElementById('resultCount');

    btn.disabled = true;
    btn.textContent = "খোঁজা হচ্ছে...";
    rBody.innerHTML = '<div class="empty-state"><div class="empty-icon">⏳</div>অনুসন্ধান করা হচ্ছে...</div>';

    try {
        const res = await fetch(API + '/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                district: dist,
                upazila: upz,
                name: name,
                fatherName: father,
                motherName: mother,
                dob: dob
            })
        });

        const data = await res.json();

        if (res.ok) {
            document.getElementById('sidebarBal').textContent = data.new_balance;
            rCount.textContent = `${data.results.length} জন পাওয়া গেছে`;

            if (data.results.length === 0) {
                rBody.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div>কোনো তথ্য খুঁজে পাওয়া যায়নি!</div>';
            } else {
                let html = '<div class="cards-grid">';
                data.results.forEach((v, i) => {
                    html += `
                    <div class="voter-card">
                        <div class="card-header">
                            <span class="voter-no">🆔 ক্রমিক: ${i+1}</span>
                            <span class="voter-meta">নং: ${v.voter_no}</span>
                        </div>
                        <div class="card-body">
                            <div class="info-label">নাম</div>
                            <div class="info-value name-highlight">${v.name}</div>
                            
                            <div class="info-label">পিতার নাম</div>
                            <div class="info-value">${v.father_name}</div>
                            
                            <div class="info-label">মাতার নাম</div>
                            <div class="info-value">${v.mother_name}</div>
                            
                            <div class="info-label">জন্ম তারিখ</div>
                            <div class="info-value">${v.dob}</div>
                            
                            <div class="info-label">ঠিকানা</div>
                            <div class="info-value">${v.upazila}, ${v.district}</div>
                        </div>
                    </div>`;
                });
                html += '</div>';
                rBody.innerHTML = html;
            }
            showToast("সার্চ সফল! ৩ টাকা ব্যালেন্স কাটা হয়েছে।");
        } else if (res.status === 402) {
            rBody.innerHTML = '<div class="empty-state"><div class="empty-icon">💳</div>পর্যাপ্ত ব্যালেন্স নেই! রিচার্জ করুন।</div>';
            showToast(data.detail || "পর্যাপ্ত ব্যালেন্স নেই!");
        } else {
            showToast(data.detail || "সার্চ ব্যর্থ হয়েছে!");
            rBody.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div>সার্চ সম্পন্ন হয়নি।</div>';
        }
    } catch (e) {
        showToast("সার্ভার সমস্যা!");
        rBody.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div>নেটওয়ার্ক এরর!</div>';
    }

    btn.disabled = false;
    btn.textContent = "সার্চ";
}

// সাইডবার ও ইউটিলিটি ফাংশন
function toggleSidebar() {
    document.getElementById('sidebarOverlay').classList.add('open');
    document.getElementById('sidebarPanel').classList.add('open');
}

function closeSidebar() {
    document.getElementById('sidebarOverlay').classList.remove('open');
    document.getElementById('sidebarPanel').classList.remove('open');
}

function copyUid() {
    const uid = document.getElementById('sidebarUid').textContent;
    navigator.clipboard.writeText(uid);
    showToast("UID কপি হয়েছে!");
}

function logout() {
    localStorage.clear();
    window.location.reload();
}

function clearForm() {
    document.getElementById('district').value = "";
    document.getElementById('upazila').innerHTML = '<option value="">-- উপজেলা --</option>';
    document.getElementById('voterName').value = "";
    document.getElementById('fatherName').value = "";
    document.getElementById('motherName').value = "";
    document.getElementById('dob').value = "";
}

function showToast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2500);
}

// ড্রপডাউন জেলা-উপজেলা লোডার
const districts = ["ঢাকা", "চট্টগ্রাম", "টাঙ্গাইল", "পটুয়াখালী", "নওগাঁ"];
const upazilas = {
    "ঢাকা": ["ধানমন্ডি", "গুলশান", "মিরপুর", "মতিঝিল"],
    "চট্টগ্রাম": ["পটিয়া", "সীতাকুণ্ড", "রাউজান"],
    "টাঙ্গাইল": ["মধুপুর", "ঘাটাইল", "কালিহাতী"],
    "পটুয়াখালী": ["বাউফল", "গলাচিপা"],
    "নওগাঁ": ["পত্নীতলা", "ধামইরহাট"]
};

function loadUpazilas() {
    const dVal = document.getElementById('district').value;
    const uSel = document.getElementById('upazila');
    uSel.innerHTML = '<option value="">-- উপজেলা --</option>';
    if (upazilas[dVal]) {
        upazilas[dVal].forEach(u => {
            uSel.innerHTML += `<option value="${u}">${u}</option>`;
        });
    }
}

// পেজ লোড হলে চালু হবে
document.addEventListener('DOMContentLoaded', () => {
    const dSel = document.getElementById('district');
    if (dSel) {
        districts.forEach(d => {
            dSel.innerHTML += `<option value="${d}">${d}</option>`;
        });
    }
    checkAuth();
});
