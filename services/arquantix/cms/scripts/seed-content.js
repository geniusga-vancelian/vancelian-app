/**
 * Script de seed pour créer le contenu initial dans Strapi
 * À exécuter après avoir créé les Content Types dans Strapi Admin
 * 
 * Usage: node scripts/seed-content.js
 */

const axios = require('axios');

const STRAPI_URL = process.env.STRAPI_URL || 'http://localhost:1337';
const ADMIN_TOKEN = process.env.STRAPI_ADMIN_TOKEN || ''; // À obtenir depuis Strapi Admin

async function seedContent() {
  console.log('🌱 Seeding Strapi content...\n');

  if (!ADMIN_TOKEN) {
    console.log('⚠️  STRAPI_ADMIN_TOKEN non défini');
    console.log('   Ce script nécessite un token admin pour créer du contenu via API');
    console.log('   Alternative: Créer le contenu manuellement dans Strapi Admin');
    console.log('   → http://localhost:1337/admin');
    return;
  }

  const headers = {
    'Authorization': `Bearer ${ADMIN_TOKEN}`,
    'Content-Type': 'application/json',
  };

  try {
    // 1. Créer Global
    console.log('1. Création Global...');
    const globalData = {
      data: {
        branding: {
          logo: '/uploads/logo.png',
          name: 'Arquantix',
          tagline: 'Innovation Technology',
        },
        socials: {
          twitter: '',
          linkedin: '',
        },
        seo: {
          defaultTitle: 'Arquantix',
          defaultDescription: 'Arquantix - Innovation Technology',
        },
      },
    };

    try {
      const globalResponse = await axios.post(
        `${STRAPI_URL}/api/globals`,
        globalData,
        { headers }
      );
      console.log('   ✅ Global créé');
    } catch (error) {
      if (error.response?.status === 400 && error.response?.data?.error?.message?.includes('already exists')) {
        console.log('   ℹ️  Global existe déjà');
      } else {
        throw error;
      }
    }

    // 2. Créer Page FR
    console.log('2. Création Page FR (home)...');
    const pageFrData = {
      data: {
        slug: 'home',
        title: 'Accueil',
        content: '<p>Bienvenue sur Arquantix</p>',
        locale: 'fr',
        seo: {
          title: 'Arquantix - Accueil',
          description: 'Page d\'accueil Arquantix',
        },
      },
    };

    try {
      const pageFrResponse = await axios.post(
        `${STRAPI_URL}/api/pages`,
        pageFrData,
        { headers }
      );
      console.log('   ✅ Page FR créée');
    } catch (error) {
      if (error.response?.status === 400) {
        console.log('   ℹ️  Page FR existe peut-être déjà');
      } else {
        throw error;
      }
    }

    // 3. Créer Page EN
    console.log('3. Création Page EN (home)...');
    const pageEnData = {
      data: {
        slug: 'home',
        title: 'Home',
        content: '<p>Welcome to Arquantix</p>',
        locale: 'en',
        seo: {
          title: 'Arquantix - Home',
          description: 'Arquantix home page',
        },
      },
    };

    try {
      const pageEnResponse = await axios.post(
        `${STRAPI_URL}/api/pages`,
        pageEnData,
        { headers }
      );
      console.log('   ✅ Page EN créée');
    } catch (error) {
      if (error.response?.status === 400) {
        console.log('   ℹ️  Page EN existe peut-être déjà');
      } else {
        throw error;
      }
    }

    console.log('\n✅ Seed terminé!');
    console.log('\n📝 Prochaines étapes:');
    console.log('   1. Aller dans Strapi Admin: http://localhost:1337/admin');
    console.log('   2. Configurer les permissions PUBLIC:');
    console.log('      Settings → Users & Permissions → Roles → Public');
    console.log('      Activer: global (find), page (find, findOne)');
    console.log('   3. Tester: http://localhost:3001/fr');

  } catch (error) {
    console.error('❌ Erreur:', error.response?.data || error.message);
    process.exit(1);
  }
}

seedContent();


