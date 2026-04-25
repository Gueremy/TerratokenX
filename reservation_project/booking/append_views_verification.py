
@login_required
def verification_view(request):
    """
    Vista para que los usuarios suban sus documentos KYC y soliciten verificación.
    """
    # Asegurar que el usuario tenga perfil
    if not hasattr(request.user, 'profile'):
        from .models import UserProfile
        UserProfile.objects.create(user=request.user)

    profile = request.user.profile
    
    if request.method == 'POST':
        try:
            # Procesar archivos
            if 'documento_frontal' in request.FILES:
                profile.documento_identidad_frontal = request.FILES['documento_frontal']
            if 'documento_reverso' in request.FILES:
                profile.documento_identidad_reverso = request.FILES['documento_reverso']
            if 'selfie' in request.FILES:
                profile.selfie_verificacion = request.FILES['selfie']
            
            # Actualizar estado a EN REVISIÓN
            profile.kyc_status = 'REVISION'
            profile.fecha_kyc = timezone.now()
            profile.save()
            
            messages.success(request, "🎉 Solicitud enviada con éxito. Nuestro equipo revisará tus documentos en breve.")
            return redirect('verification')
            
        except Exception as e:
            messages.error(request, f"Error al subir documentos: {e}")
    
    # Contexto para el template
    context = {
        'user_profile': profile,
        'kyc_tier': profile.kyc_tier,
        'kyc_tier_label': f"Nivel {profile.kyc_tier} ({profile.get_kyc_status_display()})",
        'remaining_usd': "{:,.0f}".format(profile.remaining_limit),
        'limit_usd': "{:,.0f}".format(profile.limit_usd),
    }
    return render(request, 'booking/verification.html', context)
