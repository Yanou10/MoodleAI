document.addEventListener('DOMContentLoaded', function() {
  const calendarEl = document.getElementById('calendar');

  const funFacts = {
    '2025-05-22': "Le 22 mai 1990, Microsoft a lancé Windows 3.0.",
    '2025-05-23': "Le 23 mai est la Journée mondiale de la tortue.",
    '2025-05-24': "En 1883, le pont de Brooklyn ouvrait ses portes le 24 mai.",
    '2025-05-25': "Star Wars a été projeté pour la première fois le 25 mai 1977.",
    '2025-05-26': "Le 26 mai 1896, Dow Jones publiait pour la première fois son indice.",
    '2025-05-27': "Le 27 mai est la Journée nationale de la Résistance en France.",
    '2025-05-28': "Le 28 mai est la Journée internationale du hamburger.",
    '2025-05-29': "Edmund Hillary a gravi l'Everest le 29 mai 1953.",
    '2025-05-30': "Le 30 mai est la Journée mondiale de la sclérose en plaques.",
    '2025-05-31': "Walt Whitman est né un 31 mai (1819).",
    '2025-06-01': "Le 1er juin marque la Journée mondiale des parents.",
    '2025-06-02': "En 1953, la reine Élisabeth II fut couronnée le 2 juin.",
    '2025-06-03': "Le 3 juin est la Journée mondiale du vélo.",
    '2025-06-04': "Le 4 juin est la Journée internationale des enfants victimes innocentes d'agression.",
    '2025-06-05': "C'est la Journée mondiale de l'environnement.",
    '2025-06-06': "Le Débarquement en Normandie a eu lieu le 6 juin 1944.",
    '2025-06-07': "Prince est né le 7 juin 1958.",
    '2025-06-08': "Le 8 juin est la Journée mondiale des océans.",
    '2025-06-09': "Donald Duck est apparu pour la première fois le 9 juin 1934.",
    '2025-06-10': "Le 10 juin est la Journée mondiale des droits des travailleurs domestiques.",
    '2025-06-11': "Le 11 juin est la Journée mondiale du bien-être.",
    '2025-06-12': "Anne Frank reçut son journal le 12 juin 1942.",
    '2025-06-13': "C'est la Journée internationale de sensibilisation à l'albinisme.",
    '2025-06-14': "Le 14 juin est la Journée mondiale du don de sang.",
    '2025-06-15': "Magna Carta fut signée le 15 juin 1215.",
    '2025-06-16': "Le 16 juin est la Journée internationale de l’enfant africain.",
    '2025-06-17': "Le 17 juin est la Journée mondiale de lutte contre la désertification.",
    '2025-06-18': "L'appel du 18 juin 1940 fut lancé par De Gaulle.",
    '2025-06-19': "Garfield est apparu le 19 juin 1978.",
    '2025-06-20': "Le 20 juin est la Journée mondiale des réfugiés.",
    '2025-06-21': "Le 21 juin célèbre la Fête de la musique en France.",
    '2025-06-22': "Le 22 juin 1633, Galilée abjurait ses thèses devant l'Inquisition.",
    '2025-06-23': "Le 23 juin est la Journée olympique.",
    '2025-06-24': "Le 24 juin, c'est la Saint-Jean-Baptiste au Québec.",
    '2025-06-25': "Le 25 juin 2009, Michael Jackson nous quittait.",
    '2025-06-26': "L'ONU a été créée officiellement le 26 juin 1945.",
    '2025-06-27': "Le 27 juin est la Journée des micros, du jazz et du soleil.",
    '2025-06-28': "L'archiduc François-Ferdinand a été assassiné le 28 juin 1914.",
    '2025-06-29': "Le 29 juin est la Journée internationale des tropiques.",
    '2025-06-30': "L'astéroïde Toutatis est passé près de la Terre un 30 juin.",
    '2025-07-01': "Le 1er juillet est la fête du Canada."
  };

  function getFunFact(dateStr) {
    return funFacts[dateStr] || "Cette journée est parfaite pour apprendre quelque chose de nouveau !";
  }

  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: 'dayGridMonth',
    locale: 'fr',
    themeSystem: 'bootstrap5',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
    },
    buttonText: {
      today: "Aujourd'hui",
      month: 'Mois',
      week: 'Semaine',
      day: 'Jour',
      list: 'Liste'
    },
    editable: true,
    selectable: true,
    selectMirror: true,
    dayMaxEvents: true,
    navLinks: true,

    dateClick: function(info) {
      const fact = getFunFact(info.dateStr);
      Swal.fire({
        title: '🧠 Le savais-tu ?',
        text: fact,
        icon: 'info',
        confirmButtonText: 'Cool !',
        background: '#f0f8ff',
        confirmButtonColor: '#3085d6',
        customClass: {
          popup: 'animated fadeInDown'
        }
      });
    },

    select: function(info) {
      const start = info.startStr;
      const end = info.endStr;
      const title = prompt('Nouvel événement : Entrez un titre');
      if (title) {
        calendar.addEvent({
          title: title,
          start: start,
          end: end,
          allDay: info.allDay
        });
      }
      calendar.unselect();
    },

    eventClick: function(info) {
      if (confirm(`Voulez-vous supprimer l'événement "${info.event.title}" ?`)) {
        info.event.remove();
      }
    }
  });

  calendar.render();
});
