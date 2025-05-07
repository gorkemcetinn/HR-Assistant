let documentGraphHistory = [];


document.addEventListener('DOMContentLoaded', function() {
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const loader = document.getElementById('loader');
    const modelSelector = document.getElementById('model-selector');
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    const newChatBtn = document.querySelector('.new-chat-btn');
    const sqlAssistant = document.getElementById('sql-assistant');
    const documentAssistant = document.getElementById('document-assistant');
    const personnel = document.getElementById('personnel');
    const searchInput = document.getElementById('personnel-search');
    const functions = document.getElementById('functions');
    const functionSearchInput = document.getElementById('function-search');
    const visualSelector = document.querySelector('.visual-selector'); // Changed to target the class instead of ID
    

    visualSelector.style.display = 'none';


    if (functionSearchInput) {
        functionSearchInput.addEventListener('input', function () {
            const query = this.value.toLowerCase();
            const tbody = document.querySelector('#functions-table tbody');
            const rows = tbody.querySelectorAll('tr');

            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                const rowText = Array.from(cells).map(td => td.textContent.toLowerCase()).join(' ');
                row.style.display = rowText.includes(query) ? '' : 'none';
            });
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const query = this.value.toLowerCase();
            const tbody = document.querySelector('#personnel-table tbody');
            const rows = tbody.querySelectorAll('tr');

            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                const rowText = Array.from(cells).map(td => td.textContent.toLowerCase()).join(' ');
                if (rowText.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    let currentModel = "models/gemini-2.0-flash"; // Varsayılan model

    // Her asistan modu için ayrı sohbet geçmişlerini saklayalım
    let chatHistories = {
        'sql': [],
        'document': []
    };

    // Her asistan modu için chat mesajlarını DOM'da saklayalım
    let messagesDOM = {
        'sql': '',
        'document': ''
    };

    let currentAssistantMode = 'sql';

    // Fonksiyonlar'a tıklandığında
    functions.addEventListener('click', function() {
        setActiveMenuItem(functions);
        showSection('functions-section');
        switchToFunctions();
        loadFunctionsTable();
    });

    // SQL Asistanı'na tıklandığında
    sqlAssistant.addEventListener('click', function() {
        // Mevcut asistan modunun DOM içeriğini kaydet
        if (currentAssistantMode === 'document') {
            messagesDOM.document = chatMessages.innerHTML;
        }

        setActiveMenuItem(sqlAssistant);
        showSection('chat-section');
        switchToSQLAssistant(false); // false parametresi mesajları temizlememesini söyler
    });

    // Döküman Asistanı'na tıklandığında
    documentAssistant.addEventListener('click', function() {
        // Mevcut asistan modunun DOM içeriğini kaydet
        if (currentAssistantMode === 'sql') {
            messagesDOM.sql = chatMessages.innerHTML;
        }

        setActiveMenuItem(documentAssistant);
        showSection('chat-section');
        switchToDocumentAssistant(false); // false parametresi mesajları temizlememesini söyler
    });

    // When Personnel is clicked
    personnel.addEventListener('click', function() {
        // Mevcut asistan modunun DOM içeriğini kaydet
        if (currentAssistantMode === 'sql') {
            messagesDOM.sql = chatMessages.innerHTML;
        } else if (currentAssistantMode === 'document') {
            messagesDOM.document = chatMessages.innerHTML;
        }

        setActiveMenuItem(personnel);
        showSection('personnel-section');
        switchToPersonnel();
        loadPersonnelTable();
    });

    function showSection(sectionId) {
        const sections = document.querySelectorAll('#content-sections > div');
        sections.forEach(sec => sec.style.display = 'none');

        const activeSection = document.getElementById(sectionId);
        if (activeSection) {
            activeSection.style.display = 'block';
        }

        const newChatBtn = document.querySelector('.new-chat-btn');

        if (sectionId === 'chat-section') {
            document.querySelector('.chat-container').style.display = 'flex';
            document.getElementById('personnel-section').style.display = 'none';
            document.getElementById('functions-section').style.display = 'none';
            newChatBtn.style.display = 'inline-flex'; // Show new chat button
        } else if (sectionId === 'personnel-section') {
            document.querySelector('.chat-container').style.display = 'none';
            document.getElementById('functions-section').style.display = 'none';
            document.getElementById('personnel-section').style.display = 'block';
            newChatBtn.style.display = 'none'; // Hide new chat button
        } else if (sectionId === 'functions-section') {
            document.querySelector('.chat-container').style.display = 'none';
            document.getElementById('personnel-section').style.display = 'none';
            document.getElementById('functions-section').style.display = 'block';
            newChatBtn.style.display = 'none';
        }
    }


 function loadFunctionsTable() {
    const tbody = document.querySelector('#functions-table tbody');
    tbody.innerHTML = `
        <tr>
            <td colspan="3" class="loading-message">
                <i class="fas fa-spinner fa-spin"></i> Araçlar yükleniyor...
            </td>
        </tr>
    `;

    fetch('/api/user-functions')
        .then(res => res.json())
        .then(data => {
            tbody.innerHTML = '';

            if (data.status === 'success' && Array.isArray(data.functions)) {
                if (data.functions.length === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="3" class="no-functions-message">
                                Size atanmış herhangi bir fonksiyon bulunamadı.
                            </td>
                        </tr>
                    `;
                } else {
                    data.functions.forEach(func => {
                        const row = `
                            <tr>
                                <td>${func.id}</td>
                                <td>${func.name}</td>
                                <td>${func.description}</td>
                            </tr>
                        `;
                        tbody.innerHTML += row;
                    });
                }

                document.getElementById('functions-section').style.display = 'block';
                document.querySelector('.chat-container').style.display = 'none';

                // "createGraphInfoTable();" çağrısı buradan kaldırıldı
            } else {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="3" class="error-message">
                            Fonksiyon listesi alınamadı: ${data.message || 'Bilinmeyen hata'}
                        </td>
                    </tr>
                `;
            }
        })
        .catch(err => {
            console.error('Fonksiyon verilerini alırken hata oluştu:', err);
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" class="error-message">
                        Fonksiyon listesi yüklenirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.
                    </td>
                </tr>
            `;
        });
}

    function loadPersonnelTable() {
        fetch('/api/get-employees')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    const tbody = document.querySelector('#personnel-table tbody');
                    tbody.innerHTML = ''; // Clear the table first

                    data.employees.forEach(emp => {
                        const row = `
                            <tr>   
                                <td>${emp.username}</td>
                                <td>${emp.fullname}</td>
                                <td>${emp.email}</td>
                                <td>${emp.salary}</td>
                                <td>${emp.department}</td>
                            </tr>
                        `;
                        tbody.innerHTML += row;
                    });

                    // Show personnel section
                    document.getElementById('personnel-section').style.display = 'block';
                    // Hide other sections
                    document.querySelector('.chat-container').style.display = 'none';
                } else {
                    alert('Personnel list could not be retrieved: ' + data.message);
                }
            })
            .catch(err => {
                console.error('Error retrieving personnel data:', err);
            });
    }

    // Aktif menü öğesini değiştiren fonksiyon
    // Function to change active menu item
    function setActiveMenuItem(menuItem) {
        // Remove active class from all menu items
        document.querySelectorAll('.menu-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add active class to selected menu item
        menuItem.classList.add('active');
    }

    // SQL Asistanı moduna geçiş
    // Switch to SQL Assistant mode
    function switchToSQLAssistant(clearMessages = true) {
        // Önceki asistan modu hangisiydi
        const previousMode = currentAssistantMode;
        currentAssistantMode = 'sql';

        if (clearMessages) {
            // Yeni sohbet başlatıyoruz, her şeyi temizle
            clearChatAndShowWelcome('SQL Asistanı', 'Merhaba! SQL sorguları konusunda size nasıl yardımcı olabilirim?');
            chatHistories.sql = []; // SQL mesaj geçmişini sıfırla
        } else {
            // Kayıtlı SQL mesajları varsa, onları göster
            if (messagesDOM.sql) {
                chatMessages.innerHTML = messagesDOM.sql;
            } else {
                // İlk kez SQL asistanına geçiyorsa, karşılama mesajı göster
                clearChatAndShowWelcome('SQL Asistanı', 'Merhaba! SQL sorguları konusunda size nasıl yardımcı olabilirim?');
            }
        }

        // Hide visual selection button
        visualSelector.style.display = 'none';

        updateSuggestions([
            'Kendi bilgilerimi görmek istiyorum',
            'Bütün çalışanları tablola',
            'Yeni kişi nasıl eklerim ?',
            'Çalışan silme işlemini nasıl yaparım ?',
            'Şirketteki ortalama maaş ücreti ne kadar ?'
        ]);

        // Sayfa başlığını güncelle
        document.querySelector('.page-title h1').textContent = 'SQL Asistanı';
    }

    // Döküman Asistanı moduna geçiş
// Döküman Asistanı moduna geçiş - DÜZELTİLMİŞ SÜRÜM
function switchToDocumentAssistant(clearMessages = true) {
  // Önceki asistan modu hangisiydi
  const previousMode = currentAssistantMode;
  currentAssistantMode = 'document';

  if (clearMessages) {
    // Yeni sohbet başlatıyoruz, her şeyi temizle
    clearChatAndShowWelcome('Döküman Asistanı', 'Merhaba! Yüklenen belgelerinizle ilgili sorularınızı yanıtlayabilirim.');
    chatHistories.document = []; // Döküman mesaj geçmişini sıfırla
    documentGraphHistory = []; // Grafik geçmişini de sıfırla
    messagesDOM.document = ''; // DOM içeriğini sıfırla
  } else {
    // Kayıtlı belge mesajları varsa, onları göster
    if (messagesDOM.document) {
      chatMessages.innerHTML = messagesDOM.document;

      // Grafikleri yeniden çizme işlemini bir mikrosaniye geciktir
      // Bu, DOM'un tamamen yüklenmesini sağlar
      setTimeout(() => {
        console.log("Döküman asistanı: DOM yüklendi, grafikler yeniden çiziliyor. Grafik sayısı: ", documentGraphHistory.length);

        // Tüm grafikleri yeniden çiz
        documentGraphHistory.forEach((g, index) => {
          const canvas = document.getElementById(g.canvasId);
          if (canvas) {
            console.log(`Grafik ${index + 1} yeniden çiziliyor: ${g.canvasId}`);
            renderGraphOnCanvas(canvas, g.graphData, g.graphType);
          } else {
            console.warn(`Grafik ${index + 1} için canvas bulunamadı: ${g.canvasId}`);
          }
        });
      }, 100);
    } else {
      // İlk kez belge asistanına geçiyorsa, karşılama mesajı göster
      clearChatAndShowWelcome('Döküman Asistanı', 'Merhaba! Yüklenen belgelerinizle ilgili sorularınızı yanıtlayabilirim.');
    }
  }

  // Show visual selection button
  visualSelector.style.display = 'flex';

  updateSuggestions([
    'Denetim Madde 12 nedir?',
    'Botları neden çıkarmalıyız?',
    'Departmanların performans skorlarını göster.',
    'Neden kemerlerimizi çıkarıyoruz? ',
    'Kontrol noktasında güvenlikler nasıl çalışmalıdır?',
  ]);

  // Sayfa başlığını güncelle
  document.querySelector('.page-title h1').textContent = 'Döküman Asistanı';
}

    // Switch to Personnel mode
    function switchToPersonnel() {
        currentAssistantMode = 'personnel';
        // Hide visual selection button
        visualSelector.style.display = 'none';
        clearChatAndShowWelcome('Personel Listesi');
    }

    function switchToFunctions() {
        currentAssistantMode = 'functions';
        // Hide visual selection button
        visualSelector.style.display = 'none';
        clearChatAndShowWelcome('Fonksiyon Listesi');
    }

    // Sohbeti temizleyip karşılama mesajı gösteren fonksiyon
    function clearChatAndShowWelcome(assistantName, welcomeMessage = '') {
        // Sohbet alanını temizle
        chatMessages.innerHTML = '';

        if (welcomeMessage) {
            // Karşılama mesajını ekle
            const welcomeHTML = `
                <div class="message agent-message">
                    <div class="message-avatar">
                        <i class="fas fa-robot"></i>
                    </div>
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-sender">${assistantName}</span>
                            <span class="message-time">${getCurrentTime()}</span>
                        </div>
                        <div class="message-text">
                            ${welcomeMessage}
                        </div>
                    </div>
                </div>
            `;

            chatMessages.innerHTML = welcomeHTML;
        }

        // Sayfa başlığını güncelle
        document.querySelector('.page-title h1').textContent = assistantName;
    }

    // Öneri çiplerini güncelleyen fonksiyon
    function updateSuggestions(suggestions) {
        const suggestionsContainer = document.querySelector('.input-suggestions');
        suggestionsContainer.innerHTML = '';

        suggestions.forEach(suggestion => {
            const chip = document.createElement('div');
            chip.className = 'suggestion-chip';
            chip.textContent = suggestion;

            // Öneri çipine tıklanınca girdi alanına ekle
            chip.addEventListener('click', function() {
                userInput.value = suggestion;
                userInput.focus();
            });

            suggestionsContainer.appendChild(chip);
        });
    }

    // Mevcut zamanı formatlayan yardımcı fonksiyon
    function getCurrentTime() {
        const now = new Date();
        return `Bugün, ${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`;
    }

    // Mesaj gönderme işlemi
    sendButton.addEventListener('click', sendMessage);

    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Tarih formatı yardımcı fonksiyonu
    function formatCurrentTime() {
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        return `Bugün, ${hours}:${minutes}`;
    }

    // Yeni sohbet butonu
    if (newChatBtn) {
        newChatBtn.addEventListener('click', function() {
            if (confirm('Yeni bir sohbet başlatmak istediğinize emin misiniz? Mevcut sohbetiniz kaydedilmeyecek ve geçmiş sıfırlanacak.')) {
                // Mevcut asistan modu için geçmişi sıfırla
                if (currentAssistantMode === 'sql') {
                    chatHistories.sql = [];
                    messagesDOM.sql = '';
                } else if (currentAssistantMode === 'document') {
                    chatHistories.document = [];
                    messagesDOM.document = '';
                }

                chatMessages.innerHTML = '';

                // Backend'e hafızayı temizleme isteği gönder
                fetch('/api/clear-chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    console.log("Sohbet geçmişi temizlendi:", data);

                    // İlgili asistan moduna göre karşılama mesajını göster
                    const assistantName = currentAssistantMode === 'sql' ? 'SQL Asistanı' :
                            currentAssistantMode === 'document' ? 'Döküman Asistanı' : 'Personel Asistanı';
                    const welcomeMessage = currentAssistantMode === 'sql' ? 'Merhaba! SQL sorguları konusunda size nasıl yardımcı olabilirim?' :
                            currentAssistantMode === 'document' ? 'Merhaba! Yüklenen belgelerinizle ilgili sorularınızı yanıtlayabilirim.' : 'Merhaba! Personel işlemleri konusunda size nasıl yardımcı olabilirim?';

                    addMessage({
                        sender: assistantName,
                        text: welcomeMessage,
                        time: formatCurrentTime(),
                        isAgent: true
                    });
                })
                .catch(error => {
                    console.error("Sohbet temizleme hatası:", error);
                });
            }
        });
    }

    // Öneri çipleri tıklama olayları
    suggestionChips.forEach(chip => {
        chip.addEventListener('click', function() {
            userInput.value = this.textContent;
            sendMessage();
        });
    });

    // Model değişikliğini izle
    modelSelector.addEventListener('change', function() {
        const newModel = this.value;
        if (newModel !== currentModel) {
            // Model değişikliğinde yükleme animasyonu göster
            loader.style.display = 'block';

            // Model değişikliğini backend'e bildir
            fetch('/api/change-model', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ model: newModel }),
            })
            .then(response => response.json())
            .then(data => {
                loader.style.display = 'none';

                // Başarılı model değişikliği mesajı göster
                if (data.status === 'success') {
                    addMessage({
                        sender: 'Sistem',
                        text: data.message,
                        time: formatCurrentTime(),
                        isAgent: true,
                        status: 'success'
                    });
                    currentModel = newModel;
                } else {
                    addMessage({
                        sender: 'Sistem',
                        text: data.message,
                        time: formatCurrentTime(),
                        isAgent: true,
                        status: 'error'
                    });
                }
            })
            .catch(error => {
                loader.style.display = 'none';
                addMessage({
                    sender: 'Sistem',
                    text: 'Model değiştirme sırasında bir hata oluştu: ' + error.message,
                    time: formatCurrentTime(),
                    isAgent: true,
                    status: 'error'
                });
            });
        }
    });

    // Gönder butonu ile mesaj gönderme
    sendButton.addEventListener('click', sendMessage);

    // Menü öğelerine tıklama işlevi
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', function() {
            // Aktif sınıfını yönet
            menuItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // Mesaj gönderme fonksiyonu
    // Mesaj gönderme fonksiyonunda düzeltilmiş kısım
function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
    const username = document.getElementById('username').textContent;

    // Kullanıcı mesajını ekle
    addMessage({
        sender: username,
        text: message,
        time: formatCurrentTime(),
        isAgent: false
    });

    // Sohbet geçmişine ekle - asistan moduna göre
    if (currentAssistantMode === 'sql') {
        chatHistories.sql.push({ role: 'user', content: message });
    } else if (currentAssistantMode === 'document') {
        chatHistories.document.push({ role: 'user', content: message });
    }

    // Girdi alanını temizle
    userInput.value = '';

    // Yükleniyor göstergesi
    document.getElementById('loader').style.display = 'flex';

    // API endpoint'ini moda göre seç
    let endpoint = '/api/chat';
    if (currentAssistantMode === 'document') {
        endpoint = '/api/document-chat';
    } else if (currentAssistantMode === 'personnel') {
        endpoint = '/api/personnel-chat';
    }

    // Model seçiciden seçilmiş modeli al
    const selectedModel = document.getElementById('model-selector').value;
    // Yeni görsel modlarını kullan: normal_mode veya text_only
    const visualMode = document.querySelector('input[name="visual-mode"]:checked')?.value || 'normal_mode';

    // İlgili asistan modunun chat geçmişini kullan
    const currentHistory = currentAssistantMode === 'sql' ? chatHistories.sql :
                       currentAssistantMode === 'document' ? chatHistories.document : [];

    // API isteği gönder
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            model: selectedModel,
            mode: currentAssistantMode,
            history: currentHistory,
            visual_mode: visualMode
        }),
    })
    .then(response => response.json())
    .then(data => {
        // Yükleniyor göstergesini gizle
        document.getElementById('loader').style.display = 'none';

        const response = data.response;
        const imagePath = data.image_path;
        const graphData = data.graph_data;
        const graphType = data.graph_type;

        // Asistan adını moda göre belirle
        const assistantName = currentAssistantMode === 'sql' ? 'SQL Asistanı' :
                            currentAssistantMode === 'document' ? 'Döküman Asistanı' : 'Personel Asistanı';

        // Yanıt tipine göre işleme
        if (typeof response === 'object') {
            if (response.type === 'table') {
                addMessage({
                    sender: assistantName,
                    text: response.message + "<br><br>" + response.data, // HTML tabloyu direkt ekle
                    time: formatCurrentTime(),
                    isAgent: true
                });

                // Sohbet geçmişine ekle - asistan moduna göre
                if (currentAssistantMode === 'sql') {
                    chatHistories.sql.push({ role: 'assistant', content: response.message });
                } else if (currentAssistantMode === 'document') {
                    chatHistories.document.push({ role: 'assistant', content: response.message });
                }

                // DOM içeriğini güncelle
                if (currentAssistantMode === 'sql') {
                    messagesDOM.sql = chatMessages.innerHTML;
                } else if (currentAssistantMode === 'document') {
                    messagesDOM.document = chatMessages.innerHTML;
                }
            } else if (response.status === 'success' || response.status === 'error') {
                addMessage({
                    sender: 'Sistem',
                    text: response.message,
                    time: formatCurrentTime(),
                    isAgent: true,
                    status: response.status
                });

                // DOM içeriğini güncelle
                if (currentAssistantMode === 'sql') {
                    messagesDOM.sql = chatMessages.innerHTML;
                } else if (currentAssistantMode === 'document') {
                    messagesDOM.document = chatMessages.innerHTML;
                }
            } else {
                addMessage({
                    sender: assistantName,
                    text: JSON.stringify(response),
                    time: formatCurrentTime(),
                    isAgent: true
                });

                // Sohbet geçmişine ekle - asistan moduna göre
                if (currentAssistantMode === 'sql') {
                    chatHistories.sql.push({ role: 'assistant', content: JSON.stringify(response) });
                } else if (currentAssistantMode === 'document') {
                    chatHistories.document.push({ role: 'assistant', content: JSON.stringify(response) });
                }

                // DOM içeriğini güncelle
                if (currentAssistantMode === 'sql') {
                    messagesDOM.sql = chatMessages.innerHTML;
                } else if (currentAssistantMode === 'document') {
                    messagesDOM.document = chatMessages.innerHTML;
                }
            }
        } else {
            // Eğer cevap tablo HTML'si ise, direkt HTML olarak ekle
            if (typeof response === 'string' && response.trim().startsWith('<table')) {
                const messageDiv = document.createElement('div');
                messageDiv.classList.add('message', 'agent-message');
                messageDiv.innerHTML = `
                    <div class="message-avatar"><i class="fas fa-robot"></i></div>
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-sender">${assistantName}</span>
                            <span class="message-time">${formatCurrentTime()}</span>
                        </div>
                        <div class="message-text">${response}</div>
                    </div>
                `;
                chatMessages.appendChild(messageDiv);
                scrollToBottom();

                // DOM içeriğini güncelle
                if (currentAssistantMode === 'sql') {
                    messagesDOM.sql = chatMessages.innerHTML;
                } else if (currentAssistantMode === 'document') {
                    messagesDOM.document = chatMessages.innerHTML;
                }
            } else {
                let fullResponse = response;

                // Mesaj divini oluştur
                const messageDiv = document.createElement('div');
                messageDiv.classList.add('message', 'agent-message');

                // Avatar ve temel mesaj içeriğini oluştur
                const messageContent = document.createElement('div');
                messageContent.classList.add('message-content');

                messageDiv.innerHTML = `
                    <div class="message-avatar"><i class="fas fa-robot"></i></div>
                `;

                messageContent.innerHTML = `
                    <div class="message-header">
                        <span class="message-sender">${assistantName}</span>
                        <span class="message-time">${formatCurrentTime()}</span>
                    </div>
                    <div class="message-text">${fullResponse}</div>
                `;

                messageDiv.appendChild(messageContent);

                // Görsel modu kontrolü ve içerik ekleme - GÜNCELLENMIŞ
                // Normal mod seçildiğinde görselleri göster, text_only modunda gösterme
                if (visualMode === 'normal_mode') {
                    // Görsel ekle (eğer varsa)
                    if (imagePath) {
                        const imageContainer = document.createElement('div');
                        imageContainer.className = 'document-image-container';
                        imageContainer.innerHTML = `
                            <img src="${imagePath}" alt="İlgili Görsel">
                        `;
                        messageContent.appendChild(imageContainer);
                    }

                    // Grafik ekle (eğer varsa)
                    if (graphData && graphType) {
                        const canvasId = "chart-" + Math.floor(Math.random() * 100000);
                        const graphContainer = document.createElement('div');
                        graphContainer.className = 'graph-container';
                        graphContainer.innerHTML = `<canvas id="${canvasId}" class="graph-canvas" width="100%" height="300"></canvas>`;
                        messageContent.appendChild(graphContainer);

                        // DÜZELTİLMİŞ: İndirme butonu
                        const downloadBtn = document.createElement('button');
                        downloadBtn.textContent = 'Grafiği İndir';
                        downloadBtn.className = 'download-btn';
                        downloadBtn.style.marginTop = '10px';

                        // Buton tıklama olayını düzelttik
                        downloadBtn.addEventListener('click', function() {
                            const canvas = document.getElementById(canvasId);
                            if (!canvas) {
                                console.error("Canvas bulunamadı:", canvasId);
                                return;
                            }

                            try {
                                // Canvas'ı dataURL'e dönüştür
                                const dataURL = canvas.toDataURL('image/png');

                                // İndirme bağlantısı oluştur ve kullan
                                const link = document.createElement('a');
                                link.href = dataURL;
                                link.download = 'grafik-' + new Date().toISOString().slice(0, 10) + '.png';
                                document.body.appendChild(link); // Firefox'ta gerekli
                                link.click();
                                document.body.removeChild(link); // Temizlik

                                console.log("Grafik indirme başarılı");
                            } catch (error) {
                                console.error("Grafik indirme hatası:", error);
                            }
                        });

                        messageContent.appendChild(downloadBtn);

                        // Canvas için zamanlayıcı ayarla
                        setTimeout(() => {
                            const canvas = document.getElementById(canvasId);
                            if (canvas) {
                                renderGraphOnCanvas(canvas, graphData, graphType);
                            }
                        }, 100);
                    }
                }
                // 'text_only' durumunda hiçbir görsel eklenmeyecek

                // Mesajı DOM'a ekle
                chatMessages.appendChild(messageDiv);

                // Sohbeti aşağı kaydır
                scrollToBottom();

                // Sohbet geçmişine ekle - asistan moduna göre
                if (currentAssistantMode === 'sql') {
                    chatHistories.sql.push({ role: 'assistant', content: fullResponse });
                    // SQL asistanı DOM içeriğini güncelle
                    messagesDOM.sql = chatMessages.innerHTML;
                } else if (currentAssistantMode === 'document') {
                    chatHistories.document.push({ role: 'assistant', content: fullResponse });
                    // Belge asistanı DOM içeriğini güncelle
                    messagesDOM.document = chatMessages.innerHTML;
                }
            }
        }
    })
    .catch(error => {
        document.getElementById('loader').style.display = 'none';
        addMessage({
            sender: 'Sistem',
            text: 'Sunucu ile iletişim sırasında bir hata oluştu: ' + error.message,
            time: formatCurrentTime(),
            isAgent: true,
            status: 'error'
        });

        // DOM içeriğini güncelle - hata mesajı da kaydedilsin
        if (currentAssistantMode === 'sql') {
            messagesDOM.sql = chatMessages.innerHTML;
        } else if (currentAssistantMode === 'document') {
            messagesDOM.document = chatMessages.innerHTML;
        }
    });
}


// Tema değiştirme fonksiyonları
function initThemeToggle() {
    // Header actions kısmına tema değiştirme butonu ekle
    const headerActions = document.querySelector('.header-actions');
    const themeToggleBtn = document.createElement('button');
    themeToggleBtn.className = 'theme-toggle';
    themeToggleBtn.innerHTML = '<i class="fas fa-moon"></i>';
    themeToggleBtn.setAttribute('title', 'Temayı Değiştir');
    headerActions.insertBefore(themeToggleBtn, headerActions.firstChild);

    // Önceden kaydedilmiş temayı kontrol et
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        themeToggleBtn.innerHTML = '<i class="fas fa-sun"></i>';
    }

    // Tema değiştirme olayını dinle
    themeToggleBtn.addEventListener('click', function() {
        // Temayı değiştir
        document.body.classList.toggle('dark-theme');

        // Buton ikonunu güncelle
        if (document.body.classList.contains('dark-theme')) {
            this.innerHTML = '<i class="fas fa-sun"></i>';
            localStorage.setItem('theme', 'dark');
        } else {
            this.innerHTML = '<i class="fas fa-moon"></i>';
            localStorage.setItem('theme', 'light');
        }

        // Graf oluşturulduysa, güncel tema için renklerini güncelle
        updateGraphsForTheme();
    });
}

// Tema değişikliğinde grafikleri güncelle - DÜZELTİLMİŞ SÜRÜM
function updateGraphsForTheme() {
    // Grafikler için dark tema desteğini kontrol et
    if (typeof Chart !== 'undefined' && documentGraphHistory.length > 0) {
        const isDarkTheme = document.body.classList.contains('dark-theme');
        console.log("Tema değişti, grafikleri güncelleme. Grafik sayısı:", documentGraphHistory.length);

        // Tüm grafikleri güncelle
        documentGraphHistory.forEach((g, index) => {
            const canvas = document.getElementById(g.canvasId);
            if (canvas) {
                console.log(`Güncelleniyor: Grafik ${index + 1}, ID: ${g.canvasId}`);

                // Çizelge varsa destroy et
                const chartInstance = Chart.getChart(canvas);
                if (chartInstance) {
                    chartInstance.destroy();
                    console.log(`- Eski grafik silindi: ${g.canvasId}`);
                }

                // Bir tick bekleyerek DOM'un güncellenmesini sağla
                setTimeout(() => {
                    // Grafik verilerini tema renklerine uygun şekilde yeniden oluştur
                    renderGraphOnCanvas(canvas, g.graphData, g.graphType);
                    console.log(`- Yeni grafik oluşturuldu: ${g.canvasId}`);
                }, 50);
            } else {
                console.log(`Canvas bulunamadı: ${g.canvasId}`);
            }
        });
    } else {
        console.log("Grafikler güncellenemedi: Chart tanımlı değil veya grafik geçmişi boş");
    }
}

// Geliştirilmiş grafik çizme fonksiyonu - Bu kodu script.js dosyanızdaki
// renderGraphOnCanvas fonksiyonu ile değiştirin

function renderGraphOnCanvas(canvas, data, rawType) {
  if (!canvas || !canvas.getContext) {
    console.error("Geçerli bir canvas elemanı bulunamadı:", canvas);
    return null;
  }

  const ctx = canvas.getContext('2d');
  const isDarkTheme = document.body.classList.contains('dark-theme');

  console.log(`Grafik çiziliyor: ${canvas.id}, Grafik tipi: ${rawType}, Tema: ${isDarkTheme ? 'karanlık' : 'açık'}`);
  console.log("Grafik verileri:", JSON.stringify(data, null, 2));

  // Grafik tiplerini düzgün eşleştir
  const chartTypeMap = {
    "çubuk": "bar",
    "yatay_çubuk": "bar",
    "çizgi": "line",
    "pasta": "pie",
    "alan": "line",
    "çift_eksen": "bar",
    "yığın_çubuk": "bar"
  };

  // Tema bazlı font ve renk ayarları
  Chart.defaults.font.family = "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
  Chart.defaults.font.size = 13;

  // Dark tema için renk ayarları
  const gridColor = isDarkTheme ? 'rgba(255, 255, 255, 0.1)' : 'rgba(200, 200, 200, 0.2)';
  const textColor = isDarkTheme ? '#cbd5e1' : '#333';
  const tooltipBackgroundColor = isDarkTheme ? 'rgba(26, 32, 44, 0.8)' : 'rgba(0, 0, 0, 0.8)';

  // Temel seçenekler
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: data.açıklama || "Grafik",
        font: {
          size: 18,
          weight: 'bold'
        },
        padding: {
          top: 10,
          bottom: 20
        },
        color: textColor
      },
      legend: {
        display: true,
        position: 'top',
        labels: {
          usePointStyle: true,
          padding: 15,
          color: textColor
        }
      },
      tooltip: {
        backgroundColor: tooltipBackgroundColor,
        titleFont: {
          size: 14,
          weight: 'bold'
        },
        bodyFont: {
          size: 13
        },
        padding: 12,
        cornerRadius: 6,
        displayColors: true
      }
    },
    animation: {
      duration: 1000,
      easing: 'easeOutQuart'
    }
  };

  // Grafik tipini belirle - burada string olarak karşılaştırma yapmak çok önemli
  // rawType değerini küçük harfe çevirerek kontrol edelim
  const normalizedType = rawType.toLowerCase();
  let type = chartTypeMap[normalizedType] || "bar";

  console.log("Seçilen grafik tipi:", type);

  // Pasta grafiği için özel ayarlar
  if (normalizedType === "pasta") {
    type = "pie"; // Burada tip zorla "pie" olmalı
    options.plugins.legend.position = 'right';

    // Pasta grafiği için tooltip formatını değiştir
    options.plugins.tooltip.callbacks = {
      label: function(context) {
        const label = context.label || '';
        const value = context.parsed || 0;
        const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
        const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
        return `${label}: ${value} ${data.birim || ''} (${percentage}%)`;
      }
    };

    // Pasta grafiği için scale'e gerek yok
    delete options.scales;
  } else {
    // Diğer grafikler için scale ayarları
    // Yatay çubuk için
    if (normalizedType === "yatay_çubuk") {
      options.indexAxis = 'y';
    }

    // Alan grafiği için
    if (normalizedType === "alan") {
      options.fill = true;
    }

    // Yığın çubuk için
    if (normalizedType === "yığın_çubuk") {
      options.scales = {
        x: {
          stacked: true,
          grid: {
            display: false
          },
          ticks: {
            color: textColor
          }
        },
        y: {
          stacked: true,
          grid: {
            color: gridColor
          },
          ticks: {
            color: textColor
          }
        }
      };
    } else {
      // Diğer tüm grafikler için temel ölçek ayarları
      options.scales = {
        x: {
          grid: {
            display: false
          },
          ticks: {
            color: textColor
          }
        },
        y: {
          grid: {
            color: gridColor
          },
          ticks: {
            color: textColor
          }
        }
      };
    }

    // Çift eksen için özel ayarlar
    if (normalizedType === "çift_eksen" && Array.isArray(data.values) && data.values.length >= 2) {
      options.scales = {
        x: {
          grid: {
            display: false
          },
          ticks: {
            color: textColor
          }
        },
        y: {
          type: 'linear',
          display: true,
          position: 'left',
          grid: {
            color: gridColor
          },
          ticks: {
            color: textColor
          },
          title: {
            display: true,
            text: data.seri_isimleri ? data.seri_isimleri[0] : 'Birincil',
            color: textColor
          }
        },
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          grid: {
            drawOnChartArea: false
          },
          ticks: {
            color: textColor
          },
          title: {
            display: true,
            text: data.seri_isimleri && data.seri_isimleri.length > 1 ?
                  data.seri_isimleri[1] : 'İkincil',
            color: textColor
          }
        }
      };
    }
  }

  // Tema bazlı renk dizisi
  // Dark temada daha parlak renkler
  function getChartColors(count) {
    // Renk paletleri
    const lightColors = [
      'rgba(3, 169, 244, 0.85)',
      'rgba(233, 30, 99, 0.85)',
      'rgba(255, 87, 34, 0.85)',
      'rgba(76, 175, 80, 0.85)',
      'rgba(156, 39, 176, 0.85)',
      'rgba(255, 193, 7, 0.85)',
      'rgba(0, 188, 212, 0.85)',
      'rgba(63, 81, 181, 0.85)',
      'rgba(139, 195, 74, 0.85)',
      'rgba(121, 85, 72, 0.85)'
    ];

    const darkColors = [
      'rgba(33, 179, 254, 0.85)',
      'rgba(253, 50, 119, 0.85)',
      'rgba(255, 107, 54, 0.85)',
      'rgba(86, 195, 90, 0.85)',
      'rgba(176, 59, 196, 0.85)',
      'rgba(255, 213, 27, 0.85)',
      'rgba(20, 208, 232, 0.85)',
      'rgba(83, 101, 201, 0.85)',
      'rgba(159, 215, 94, 0.85)',
      'rgba(141, 105, 92, 0.85)'
    ];

    const colors = isDarkTheme ? darkColors : lightColors;
    return Array(count).fill(0).map((_, i) => colors[i % colors.length]);
  }

  // Transparan border renkleri için
  function getBorderColors(colors) {
    return colors.map(color => color.replace('0.85', '1'));
  }

  // Gradient arka planlar
  function createGradients(ctx, colors) {
    return colors.map(color => {
      const gradient = ctx.createLinearGradient(0, 0, 0, 400);
      gradient.addColorStop(0, color);
      gradient.addColorStop(1, color.replace('0.85)', '0.1)'));
      return gradient;
    });
  }

  // Var olan Chart varsa sil
  const existingChart = Chart.getChart(canvas);
  if (existingChart) {
    existingChart.destroy();
    console.log("Mevcut grafik silindi");
  }

  // Grafik verilerini hazırla
  const datasets = [];

  // Hem labels hem de values'un array olduğundan emin olalım
  if (!Array.isArray(data.labels)) {
    console.error("Etiketler dizisi değil:", data.labels);
    data.labels = ["Veri Yok"];
  }

  if (!Array.isArray(data.values)) {
    console.error("Değerler dizisi değil:", data.values);
    data.values = [0];
  }

  // Renk paletini al
  let backgroundColors;
  let borderColors;

  // Pasta grafiği için özel veri hazırlama
  if (type === "pie") {
    const labelCount = data.labels.length;
    backgroundColors = getChartColors(labelCount);
    borderColors = getBorderColors(backgroundColors);

    // Pasta grafiği için tek seri yeterli
    datasets.push({
      label: data.seri_isimleri && data.seri_isimleri.length > 0 ? data.seri_isimleri[0] : "Veri",
      data: Array.isArray(data.values[0]) ? data.values[0] : data.values,
      backgroundColor: backgroundColors,
      borderColor: isDarkTheme ? 'rgba(26, 32, 44, 0.8)' : 'rgba(255, 255, 255, 0.8)',
      borderWidth: 2,
      hoverOffset: 10
    });
  }
  // Diğer grafik türleri için veri hazırlama
  else if (Array.isArray(data.values[0])) {
    // Çoklu seri
    const seriesCount = data.values.length;
    backgroundColors = getChartColors(seriesCount);
    borderColors = getBorderColors(backgroundColors);

    // Çift eksen grafiği için özel yapılandırma
    if (normalizedType === "çift_eksen" && seriesCount >= 2) {
      // Birinci seri için
      datasets.push({
        label: data.seri_isimleri && data.seri_isimleri.length > 0 ? data.seri_isimleri[0] : `Seri 1`,
        data: data.values[0],
        backgroundColor: backgroundColors[0],
        borderColor: borderColors[0],
        borderWidth: 2,
        yAxisID: 'y',
        tension: 0.3
      });

      // İkinci seri için (farklı eksen)
      datasets.push({
        label: data.seri_isimleri && data.seri_isimleri.length > 1 ?
              data.seri_isimleri[1] : `Seri 2`,
        data: data.values[1],
        backgroundColor: backgroundColors[1],
        borderColor: borderColors[1],
        borderWidth: 2,
        yAxisID: 'y1',
        tension: 0.3,
        type: 'line'
      });

      // Diğer seriler için
      for (let i = 2; i < seriesCount; i++) {
        datasets.push({
          label: data.seri_isimleri && data.seri_isimleri.length > i ?
                data.seri_isimleri[i] : `Seri ${i+1}`,
          data: data.values[i],
          backgroundColor: backgroundColors[i],
          borderColor: borderColors[i],
          borderWidth: 2,
          yAxisID: i % 2 === 0 ? 'y' : 'y1',
          tension: 0.3
        });
      }
    } else {
      // Normal çoklu seri
      data.values.forEach((vals, i) => {
        // Alan grafiği için gradientleri kullan
        const bgColor = normalizedType === "alan" ?
                      createGradients(ctx, [backgroundColors[i]])[0] :
                      backgroundColors[i];

        datasets.push({
          label: data.seri_isimleri && data.seri_isimleri.length > i ?
                data.seri_isimleri[i] : `Seri ${i+1}`,
          data: vals,
          backgroundColor: type === "line" && normalizedType !== "alan" ? 'rgba(0,0,0,0)' : bgColor,
          borderColor: borderColors[i],
          borderWidth: 2,
          fill: normalizedType === "alan",
          tension: 0.3,
          borderRadius: type === "bar" ? 4 : 0
        });
      });
    }
  } else {
    // Tek seri
    const labelCount = data.labels.length;
    backgroundColors = getChartColors(labelCount);
    borderColors = getBorderColors(backgroundColors);

    if (type === "bar") {
      datasets.push({
        label: data.seri_isimleri && data.seri_isimleri.length > 0 ? data.seri_isimleri[0] : "Veri",
        data: data.values,
        backgroundColor: normalizedType === "çubuk" ? backgroundColors : backgroundColors[0],
        borderColor: normalizedType === "çubuk" ? borderColors : borderColors[0],
        borderWidth: 2,
        borderRadius: 4
      });
    } else {
      datasets.push({
        label: data.seri_isimleri && data.seri_isimleri.length > 0 ? data.seri_isimleri[0] : "Veri",
        data: data.values,
        backgroundColor: type === "line" && normalizedType !== "alan" ? 'rgba(0,0,0,0)' : backgroundColors[0],
        borderColor: borderColors[0],
        borderWidth: 3,
        fill: normalizedType === "alan",
        tension: 0.3,
        borderRadius: 0
      });
    }
  }

  try {
    // Oluşacak grafiği logla
    console.log(`Grafik oluşturuluyor: ${type}`, {
      labels: data.labels,
      datasets: datasets,
      options: options
    });

    // Grafik nesnesi oluştur
    const chart = new Chart(ctx, {
      type: type,
      data: {
        labels: data.labels,
        datasets: datasets
      },
      options: options
    });

    console.log(`Grafik başarıyla çizildi: ${canvas.id}`);

    // Grafik geçmişine ekle veya güncelle
    const existingGraphIndex = documentGraphHistory.findIndex(g => g.canvasId === canvas.id);
    if (existingGraphIndex === -1) {
      // Yeni grafik
      documentGraphHistory.push({
        canvasId: canvas.id,
        graphData: data,
        graphType: rawType
      });
      console.log(`Yeni grafik geçmişe eklendi: ${canvas.id}`);
    } else {
      // Var olan grafiği güncelle
      documentGraphHistory[existingGraphIndex] = {
        canvasId: canvas.id,
        graphData: data,
        graphType: rawType
      };
      console.log(`Mevcut grafik geçmişi güncellendi: ${canvas.id}`);
    }

    return chart;
  } catch (error) {
    console.error("Grafik çizimi sırasında hata:", error, error.stack);

    // Hata durumunda basit bir mesaj göster
    ctx.font = '14px Arial';
    ctx.fillStyle = isDarkTheme ? '#fff' : '#333';
    ctx.textAlign = 'center';
    ctx.fillText('Grafik oluşturulurken hata oluştu', canvas.width / 2, canvas.height / 2);
    ctx.fillText(error.message, canvas.width / 2, canvas.height / 2 + 20);

    return null;
  }
}



    // Mesaj ekleme fonksiyonu
    function addMessage(messageData) {
        const { sender, text, time, isAgent, status, tableData } = messageData;

        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');

        if (isAgent) {
            messageDiv.classList.add('agent-message');
        } else {
            messageDiv.classList.add('user-message');
        }

        let avatarIcon = isAgent ? 'fas fa-robot' : 'fas fa-user';

        // HTML yapısını oluştur
        let messageHTML = `
            <div class="message-avatar">
                <i class="${avatarIcon}"></i>
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-sender">${sender}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-text">
                    ${status ? `<span class="${status}-message">${text}</span>` : text}
                </div>
            </div>
        `;

        messageDiv.innerHTML = messageHTML;

        // Tablo varsa ekle
        if (tableData) {
            const table = createTable(tableData);
            messageDiv.querySelector('.message-text').appendChild(table);
        }

        chatMessages.appendChild(messageDiv);

        // Sohbet alanını en alta kaydır
        scrollToBottom();
    }

    // Sohbet alanını en alta kaydırma
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Tablo oluşturma fonksiyonu
function createTable(data, headers = null) {
    const table = document.createElement('table');
    table.classList.add('table-result');

    // Veri kontrolü yap
    if (!data || data.length === 0) {
        const tbody = document.createElement('tbody');
        const emptyRow = document.createElement('tr');
        const emptyCell = document.createElement('td');
        emptyCell.textContent = 'Gösterilecek veri yok';
        emptyCell.colSpan = headers ? headers.length : 1;
        emptyCell.style.textAlign = 'center';
        emptyCell.style.padding = '20px';
        emptyRow.appendChild(emptyCell);
        tbody.appendChild(emptyRow);
        table.appendChild(tbody);
        return table;
    }

    // Başlık satırını oluştur
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');

    // Başlıkları belirle: Öncelik parametreden gelen, sonra veriden türet
    let tableHeaders = headers;

    if (!tableHeaders) {
        // Veriden başlıkları türet
        if (Array.isArray(data[0])) {
            tableHeaders = Array(data[0].length).fill(0).map((_, i) => `Sütun ${i+1}`);
        } else if (typeof data[0] === 'object' && data[0] !== null) {
            tableHeaders = Object.keys(data[0]);
        } else {
            tableHeaders = ['Değer'];
        }
    }

    // Başlıkları ekle
    tableHeaders.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header;
        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Veri satırlarını oluştur
    const tbody = document.createElement('tbody');

    data.forEach(row => {
        const tr = document.createElement('tr');

        // Satır tipine göre işle
        if (Array.isArray(row)) {
            // Dizi ise her elemanı hücre olarak ekle
            row.forEach(cell => {
                const td = document.createElement('td');
                td.textContent = cell !== null && cell !== undefined ? cell : '';
                tr.appendChild(td);
            });
        } else if (typeof row === 'object' && row !== null) {
            // Nesne ise değerlerini hücre olarak ekle
            Object.values(row).forEach(cell => {
                const td = document.createElement('td');
                td.textContent = cell !== null && cell !== undefined ? cell : '';
                tr.appendChild(td);
            });
        } else {
            // Primitif değer ise (string, number, vs) tek hücreye ekle
            const td = document.createElement('td');
            td.textContent = row !== null && row !== undefined ? row : '';
            tr.appendChild(td);
        }

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    return table;
}
    // Document viewer functionality - Add these at the end of the DOMContentLoaded event
    document.body.addEventListener('click', function(event) {
        // Check if clicked element is a source link
        if (event.target.classList.contains('source-link')) {
            event.preventDefault();

            const fileName = event.target.getAttribute('data-file');
            const pageNum = event.target.getAttribute('data-page');

            // Call function to display document viewer with specific page
            openDocumentViewer(fileName, pageNum);
        }
    });

    function openDocumentViewer(fileName, pageNum) {
        // Implement based on your document viewer solution
        const viewerUrl = `/document-viewer?file=${encodeURIComponent(fileName)}&page=${encodeURIComponent(pageNum)}`;

        // Open in a modal
        showDocumentModal(viewerUrl);
    }

    function showDocumentModal(url) {
        // Example modal implementation
        const modal = document.getElementById('documentViewerModal') || createDocumentModal();
        const iframe = modal.querySelector('iframe');
        iframe.src = url;

        // Show the modal
        modal.style.display = 'block';
    }

    function createDocumentModal() {
        // Create modal if it doesn't exist
        const modal = document.createElement('div');
        modal.id = 'documentViewerModal';
        modal.className = 'document-modal';

        modal.innerHTML = `
            <div class="document-modal-content">
                <span class="document-modal-close">&times;</span>
                <iframe width="100%" height="90%" frameborder="0"></iframe>
            </div>
        `;

        // Add close button functionality
        const closeButton = modal.querySelector('.document-modal-close');
        closeButton.onclick = function() {
            modal.style.display = 'none';
        };

        // Close when clicking outside content
        window.onclick = function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        };

        // Add modal to document
        document.body.appendChild(modal);

        // Add basic styling
        const style = document.createElement('style');
        style.innerHTML = `
            .document-modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.7);
            }
            .document-modal-content {
                background-color: #fff;
                margin: 5% auto;
                padding: 20px;
                border-radius: 5px;
                width: 80%;
                height: 80%;
            }
            .document-modal-close {
                color: #aaa;
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
            }
            .document-modal-close:hover {
                color: #000;
            }
            .document-sources {
                margin-top: 15px;
                padding: 10px;
                background-color: #f7f7f7;
                border-radius: 5px;
                border-left: 3px solid #007bff;
            }
            .source-link {
                color: #007bff;
                text-decoration: underline;
                cursor: pointer;
            }
        `;
        document.head.appendChild(style);

        return modal;
    }
    initThemeToggle();
});