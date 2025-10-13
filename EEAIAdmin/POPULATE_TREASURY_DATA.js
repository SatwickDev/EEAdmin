/**
 * Script to populate Treasury collections with sample data
 * Run this in the browser console when the application is running
 */

async function populateTreasuryData() {
    console.log('🚀 Starting Treasury data population...');
    
    try {
        const response = await fetch('/api/test/populate-treasury', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ Treasury collections populated successfully!');
            console.log('📊 Collection Summary:');
            if (data.collections) {
                Object.entries(data.collections).forEach(([collection, count]) => {
                    console.log(`  - ${collection}: ${count} documents`);
                });
            }
        } else {
            console.error('❌ Failed to populate Treasury collections:', data.error || data.message);
        }
        
        return data;
        
    } catch (error) {
        console.error('❌ Error calling populate endpoint:', error);
        return { success: false, error: error.message };
    }
}

// Auto-execute if you want to run immediately
console.log('Treasury data population script loaded.');
console.log('To populate Treasury collections, run: populateTreasuryData()');

// Optional: Run immediately
// populateTreasuryData();