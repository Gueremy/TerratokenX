
@login_required
def verification(request):
    """
    Vista para subir documentos KYC.
    """
    # Defensive check: crear perfil si no existe
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.get_or_create(user=request.user)
    
    profile = request.user.profile
    
    if request.method == 'POST':
        try:
            updated = False
            # Procesar archivos
            if 'documento_frontal' in request.FILES:
                profile.documento_identidad_frontal = request.FILES['documento_frontal']
                updated = True
            if 'documento_reverso' in request.FILES:
                profile.documento_identidad_reverso = request.FILES['documento_reverso']
                updated = True
            if 'selfie' in request.FILES:
                profile.selfie_verificacion = request.FILES['selfie']
                updated = True
            
            if updated:
                # Cambiar estado a REVISION
                profile.kyc_status = 'REVISION' 
                profile.fecha_kyc = timezone.now()
                profile.save()
                messages.success(request, "Documentos recibidos correctamente. Tu cuenta está ahora EN REVISIÓN.")
            else:
                messages.warning(request, "No se adjuntaron documentos nuevos.")
            
            return redirect('verification')
            
        except Exception as e:
            messages.error(request, f"Error al subir documentos: {e}")
    
    context = {
        'user_profile': profile,
        'kyc_tier_label': f"Nivel {profile.kyc_tier}",
        'remaining_usd': "{:,.0f}".format(profile.remaining_limit),
    }
    return render(request, 'booking/verification.html', context)
