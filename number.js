export default async function handler(req, res) {
    // CORS enable
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET');
    
    // URL se number parameter lelo
    const { number } = req.query;
    
    // Agar number nahi diya
    if (!number) {
        return res.status(200).json({
            success: false,
            user: "@Fghgddggf",
            message: "Number chahiye bhai!",
            example: "https://prakhar-number-api.vercel.app/number?number=9693615642"
        });
    }
    
    // Help option
    if (number === "help" || number === "?help") {
        return res.status(200).json({
            success: true,
            user: "@Fghgddggf",
            message: "API Usage Guide",
            commands: {
                basic: "/number?number=YOUR_NUMBER",
                example: "/number?number=9876543210"
            }
        });
    }
    
    try {
        console.log(`🔍 Searching for: ${number}`);
        
        // Validate phone number (Indian)
        const phoneRegex = /^[6-9]\d{9}$/;
        if (!phoneRegex.test(number)) {
            return res.status(200).json({
                success: false,
                user: "@Fghgddggf",
                message: "Invalid Indian mobile number!",
                error: "Number must start with 6,7,8,9 and be 10 digits long"
            });
        }
        
        // ✅ FIX: Original API call with proper error handling
        const originalUrl = `https://all-number-info-rajan-eta.vercel.app/api?number=${number}`;
        
        let data;
        try {
            const response = await fetch(originalUrl);
            if (!response.ok) {
                throw new Error(`API returned ${response.status}`);
            }
            data = await response.json();
        } catch (fetchError) {
            console.error('Fetch error:', fetchError);
            return res.status(200).json({
                success: false,
                user: "@Fghgddggf",
                number: number,
                message: "Original API is down or unreachable",
                error: fetchError.message
            });
        }
        
        // 📌 SAB RECORDS STORE KARO (DUPLICATE KE SAATH BHI)
        const records = [];
        
        // Source 2 se data lo - SAB RECORDS (duplicate ke saath)
        const source2Data = data?.results?.source_2?.data?.data;
        if (source2Data && Array.isArray(source2Data)) {
            for (const item of source2Data) {
                records.push({
                    NAME: item.NAME || null,
                    MOBILE: item.MOBILE || null,
                    alt: item.alt || null,
                    fname: item.fname || null,
                    circle: item.circle || null,
                    ADDRESS: item.ADDRESS || null,
                    id: item.id || null,
                    email: item.email || null
                });
            }
        }
        
        // Agar source 2 mein kuch nahi mila toh source 1 se try karo
        if (records.length === 0) {
            const source1Data = data?.results?.source_1?.data?.response?.data;
            if (source1Data && Array.isArray(source1Data)) {
                for (const item of source1Data) {
                    records.push({
                        NAME: item.name || null,
                        MOBILE: item.num || null,
                        alt: item.alt || null,
                        fname: item.fname || null,
                        circle: item.circle || null,
                        ADDRESS: item.address || null,
                        id: item.aadhar || null,
                        email: item.email || null
                    });
                }
            }
        }
        
        // Agar phir bhi kuch nahi mila
        if (records.length === 0) {
            return res.status(200).json({
                success: false,
                user: "@Fghgddggf",
                number: number,
                message: "No information found for this number"
            });
        }
        
        // ✅ POORA DATA - JITNA ORIGINAL API MEIN HAI
        return res.status(200).json({
            success: true,
            user: "@Fghgddggf",
            developer: "@Fghgddggf",
            number: number,
            total_records: records.length,
            records: records,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        console.error('❌ Error:', error);
        return res.status(200).json({
            success: false,
            user: "@Fghgddggf",
            message: "Something went wrong",
            error: error.message
        });
    }
}
