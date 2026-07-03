import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  en: {
    translation: {
      common: {
        loading: 'Loading...',
        error: 'An error occurred',
        retry: 'Retry',
        cancel: 'Cancel',
        save: 'Save',
        delete: 'Delete',
        edit: 'Edit',
        search: 'Search',
        filter: 'Filter',
        export: 'Export',
        import: 'Import',
      },
      nav: {
        dashboard: 'Dashboard',
        candidates: 'Candidates',
        analyze: 'Analyze',
        jobs: 'Job Descriptions',
        interviews: 'Interviews',
        team: 'Team',
        settings: 'Settings',
      },
      candidates: {
        title: 'Candidates',
        noResults: 'No candidates found',
        addCandidate: 'Add Candidate',
        importCsv: 'Import CSV',
        searchPlaceholder: 'Search candidates...',
        filters: {
          status: 'Status',
          score: 'Score Range',
          skills: 'Skills',
        },
      },
      analyze: {
        title: 'Analyze Resume',
        uploadResume: 'Upload Resume',
        pasteJd: 'Paste Job Description',
        analyze: 'Analyze',
        results: 'Results',
      },
    },
  },
  es: {
    translation: {
      common: {
        loading: 'Cargando...',
        error: 'Ocurrió un error',
        retry: 'Reintentar',
        cancel: 'Cancelar',
        save: 'Guardar',
        delete: 'Eliminar',
        edit: 'Editar',
        search: 'Buscar',
        filter: 'Filtrar',
        export: 'Exportar',
        import: 'Importar',
      },
      nav: {
        dashboard: 'Panel',
        candidates: 'Candidatos',
        analyze: 'Analizar',
        jobs: 'Descripciones',
        interviews: 'Entrevistas',
        team: 'Equipo',
        settings: 'Configuración',
      },
      candidates: {
        title: 'Candidatos',
        noResults: 'No se encontraron candidatos',
        addCandidate: 'Agregar Candidato',
        importCsv: 'Importar CSV',
        searchPlaceholder: 'Buscar candidatos...',
      },
      analyze: {
        title: 'Analizar Currículum',
        uploadResume: 'Subir Currículum',
        pasteJd: 'Pegar Descripción',
        analyze: 'Analizar',
        results: 'Resultados',
      },
    },
  },
  fr: {
    translation: {
      common: {
        loading: 'Chargement...',
        error: 'Une erreur est survenue',
        retry: 'Réessayer',
        cancel: 'Annuler',
        save: 'Enregistrer',
        delete: 'Supprimer',
        edit: 'Modifier',
        search: 'Rechercher',
        filter: 'Filtrer',
        export: 'Exporter',
        import: 'Importer',
      },
      nav: {
        dashboard: 'Tableau de bord',
        candidates: 'Candidats',
        analyze: 'Analyser',
        jobs: 'Descriptions',
        interviews: 'Entretiens',
        team: 'Équipe',
        settings: 'Paramètres',
      },
      candidates: {
        title: 'Candidats',
        noResults: 'Aucun candidat trouvé',
        addCandidate: 'Ajouter un candidat',
        importCsv: 'Importer CSV',
        searchPlaceholder: 'Rechercher des candidats...',
      },
      analyze: {
        title: 'Analyser le CV',
        uploadResume: 'Télécharger le CV',
        pasteJd: 'Coller la description',
        analyze: 'Analyser',
        results: 'Résultats',
      },
    },
  },
}

i18n.use(initReactI18next).init({
  resources,
  lng: 'en',
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false,
  },
})

export default i18n
