# New mood endpoint that handles URLs from frontend

@app.post("/api/mood")
async def submit_mood(
    request: Request,
    user_id_obj: dict = Depends(verify_token)
):
    """Submit mood entry: accepts JSON with URLs or form-data with files"""
    try:
        content_type = request.headers.get("content-type", "")
        
        # Handle JSON (URLs from frontend Supabase upload)
        if "application/json" in content_type:
            data = await request.json()
            user_id = data.get("id")
            mood_text = data.get("mood_text")
            audio_url = data.get("audio_url")
            image_url = data.get("image_url")
            
            logger.info(f"Processing mood entry via URLs for user: {user_id}")
            logger.info(f"Audio URL: {audio_url}")
            logger.info(f"Image URL: {image_url}")
            
            # Download files from URLs if provided
            import requests
            import tempfile
            
            audio_path = None
            image_path = None
            
            if audio_url:
                resp = requests.get(audio_url)
                audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".audio").name
                with open(audio_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Downloaded audio to: {audio_path}")
            
            if image_url:
                resp = requests.get(image_url)
                image_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                with open(image_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Downloaded image to: {image_path}")
            
            # Process with ML models
            if preprocessor and analyzer:
                logger.info("Using ML models with downloaded files")
                preprocessed_data = preprocessor.preprocess(
                    audio_path=audio_path,
                    image_path=image_path,
                    text_input=mood_text,
                    user_id=user_id,
                    analyze=True
                )
                
                # Cleanup temp files
                if audio_path and os.path.exists(audio_path):
                    os.unlink(audio_path)
                if image_path and os.path.exists(image_path):
                    os.unlink(image_path)
                
                analysis_result = preprocessed_data.get("analysis_result", {})
                recommendations = analysis_result.get("analysis", "") if analysis_result else ""
                
                if not recommendations:
                    recommendations = "Analysis in progress - recommendations will be available shortly."
                
                # Save to database
                mood_entry = {
                    "id": user_id,
                    "mood_text": mood_text,
                    "audio_transcript": preprocessed_data.get("audio_transcript", ""),
                    "emotion": preprocessed_data.get("emotion", ""),
                    "emotion_confidence": preprocessed_data.get("emotion_confidence", 0),
                    "recommendations": recommendations,
                    "created_at": datetime.now().isoformat()
                }
                
                supabase.table("mood_entries").insert(mood_entry).execute()
                
                return JSONResponse({
                    "status": "success",
                    "message": "Mood processed successfully",
                    "data": {
                        "user_id": user_id,
                        "mood_text": mood_text,
                        "audio_transcript": preprocessed_data.get("audio_transcript", ""),
                        "emotion": preprocessed_data.get("emotion", ""),
                        "emotion_confidence": preprocessed_data.get("emotion_confidence", 0),
                        "recommendations": recommendations,
                        "mood": analysis_result.get("mood", "") if analysis_result else "",
                        "stress_level": analysis_result.get("stress_level", 0) if analysis_result else 0,
                        "stress_day": analysis_result.get("stress_day", 0) if analysis_result else 0,
                        "stress_alert": analysis_result.get("stress_alert", None) if analysis_result else None,
                        "timestamp": datetime.now().isoformat()
                    }
                })
            
            # Fallback
            mood_analysis = analyze_mood_text(mood_text)
            return JSONResponse({
                "status": "success",
                "message": "Mood processed with fallback",
                "data": {
                    "user_id": user_id,
                    "mood_text": mood_text,
                    "emotion": mood_analysis["emotion"],
                    "emotion_confidence": mood_analysis["confidence"],
                    "recommendations": mood_analysis["recommendations"],
                    "timestamp": datetime.now().isoformat()
                }
            })
        
        # Handle multipart/form-data (legacy: files uploaded directly)
        else:
            form = await request.form()
            user_id = form.get("id")
            mood_text = form.get("mood_text")
            mood_audio = form.get("mood_audio")
            mood_image = form.get("mood_image")
            
            logger.info(f"Processing mood entry via form-data for user: {user_id}")
            
            # Save files
            audio_path = None
            image_path = None
            
            if mood_audio:
                audio_path = TEMP_DIR / f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{mood_audio.filename}"
                with open(audio_path, "wb") as f:
                    f.write(await mood_audio.read())
            
            if mood_image:
                image_path = TEMP_DIR / f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{mood_image.filename}"
                with open(image_path, "wb") as f:
                    f.write(await mood_image.read())
            
            # Process with ML
            if preprocessor and analyzer:
                preprocessed_data = preprocessor.preprocess(
                    audio_path=str(audio_path) if audio_path else None,
                    image_path=str(image_path) if image_path else None,
                    text_input=mood_text,
                    user_id=user_id,
                    analyze=True
                )
                
                analysis_result = preprocessed_data.get("analysis_result", {})
                recommendations = analysis_result.get("analysis", "") if analysis_result else ""
                
                return JSONResponse({
                    "status": "success",
                    "data": {
                        "user_id": user_id,
                        "recommendations": recommendations,
                        "timestamp": datetime.now().isoformat()
                    }
                })
            
            # Fallback
            mood_analysis = analyze_mood_text(mood_text)
            return JSONResponse({
                "status": "success",
                "data": {
                    "user_id": user_id,
                    "recommendations": mood_analysis["recommendations"],
                    "timestamp": datetime.now().isoformat()
                }
            })
    
    except Exception as e:
        logger.error(f"Error processing mood: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Mood processing error: {str(e)}")

