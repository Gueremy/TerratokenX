from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Proyecto, ProjectDrop
from .forms import ProjectDropForm

# ==============================================================================
# DROPS MANAGEMENT (ADMIN DIOS & FRACTIONALIZERS)
# ==============================================================================

def _get_panel_context(request, force_seller=False):
    """
    Determina qué base template y contexto usar.
    Si force_seller=True, siempre usa el panel de vendedor (verde).
    """
    is_admin = (request.user.is_superuser or request.user.is_staff) and not force_seller
    base_template = 'booking/admin/base_admin.html' if is_admin else 'booking/investor/base_investor.html'
    return is_admin, base_template


# ====================== ADMIN DIOS ======================

@login_required(login_url='login')
def admin_drops_overview(request):
    """
    Vista principal de la sección Drops en el Admin Dios.
    Lista TODOS los proyectos con sus drops asociados.
    """
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Acceso denegado.")
        return redirect('investor_dashboard')
    
    from django.utils import timezone
    now = timezone.now()
    
    proyectos = Proyecto.objects.filter(activo=True).prefetch_related('drops').order_by('-created_at')
    
    for p in proyectos:
        all_drops = p.drops.all()
        p.total_drops = all_drops.count()
        p.drops_activos = sum(1 for d in all_drops if d.activo and d.fecha_inicio <= now <= d.fecha_fin)
        p.drops_proximos = sum(1 for d in all_drops if d.activo and now < d.fecha_inicio)
        p.drops_list = all_drops.order_by('-fecha_inicio')[:5]
    
    return render(request, 'booking/admin/drops_overview.html', {
        'proyectos': proyectos,
        'active_tab': 'drops',
    })


# ====================== VENDEDOR (FRACTIONALIZER) ======================

@login_required(login_url='investor_login')
def seller_drops_overview(request):
    """
    Vista principal de Drops para el Panel de Vendedor.
    Lista solo los proyectos del vendedor con sus drops.
    """
    from django.utils import timezone
    now = timezone.now()
    
    # Superuser ve todos, vendedor normal ve solo los suyos
    if request.user.is_superuser:
        proyectos = Proyecto.objects.filter(activo=True).prefetch_related('drops').order_by('-created_at')
    else:
        proyectos = Proyecto.objects.filter(owner=request.user, activo=True).prefetch_related('drops').order_by('-created_at')
    
    for p in proyectos:
        all_drops = p.drops.all()
        p.total_drops = all_drops.count()
        p.drops_activos = sum(1 for d in all_drops if d.activo and d.fecha_inicio <= now <= d.fecha_fin)
        p.drops_proximos = sum(1 for d in all_drops if d.activo and now < d.fecha_inicio)
        p.drops_list = all_drops.order_by('-fecha_inicio')[:5]
    
    return render(request, 'booking/admin/drops_overview.html', {
        'proyectos': proyectos,
        'active_tab': 'drops',
        'base_template': 'booking/investor/base_investor.html',
        'is_seller_panel': True,
    })


# ====================== VISTAS COMPARTIDAS ======================

@login_required(login_url='login')
def admin_project_drops(request, project_id):
    """
    Lista y gestión de Drops para un proyecto específico.
    Accesible por Admin Dios y Fraccionadores.
    """
    proyecto = get_object_or_404(Proyecto, id=project_id)
    force_seller = request.GET.get('panel') == 'seller'
    
    is_admin, base_template = _get_panel_context(request, force_seller)
    is_owner = proyecto.owner == request.user
    
    if not is_admin and not is_owner:
        messages.error(request, "No tienes permiso para gestionar drops de este proyecto.")
        return redirect('investor_dashboard')

    drops = proyecto.drops.all().order_by('-fecha_inicio')
    
    tokens_totales = proyecto.tokens_totales
    tokens_asignados = sum(d.tokens_disponibles_drop for d in drops)
    tokens_libres = max(0, tokens_totales - tokens_asignados)
    porcentaje_libre = round((tokens_libres / tokens_totales) * 100, 1) if tokens_totales > 0 else 0

    return render(request, 'booking/admin/project_drops.html', {
        'proyecto': proyecto,
        'drops': drops,
        'base_template': base_template,
        'is_admin': is_admin,
        'is_seller_panel': force_seller,
        'active_tab': 'drops',
        'tokens_totales': tokens_totales,
        'tokens_asignados': tokens_asignados,
        'tokens_libres': tokens_libres,
        'porcentaje_libre': porcentaje_libre,
    })

@login_required(login_url='login')
def admin_drop_create(request, project_id):
    proyecto = get_object_or_404(Proyecto, id=project_id)
    force_seller = request.GET.get('panel') == 'seller'
    
    is_admin, base_template = _get_panel_context(request, force_seller)
    is_owner = proyecto.owner == request.user
    
    if not is_admin and not is_owner:
        messages.error(request, "No tienes permiso para crear drops en este proyecto.")
        return redirect('investor_dashboard')

    if request.method == 'POST':
        form = ProjectDropForm(request.POST, proyecto=proyecto)
        if form.is_valid():
            drop = form.save(commit=False)
            drop.proyecto = proyecto
            
            porcentaje = form.cleaned_data['porcentaje_tokens']
            drop.tokens_disponibles_drop = round(proyecto.tokens_totales * porcentaje / 100)
            
            drop.save()
            messages.success(request, "Drop creado exitosamente.")
            redirect_url = f"/admin-panel/drops/project/{proyecto.id}/"
            if force_seller:
                redirect_url += "?panel=seller"
            return redirect(redirect_url)
    else:
        form = ProjectDropForm(proyecto=proyecto)

    return render(request, 'booking/admin/drop_form.html', {
        'form': form,
        'proyecto': proyecto,
        'action': 'Crear',
        'base_template': base_template,
        'is_seller_panel': force_seller,
        'active_tab': 'drops',
    })

@login_required(login_url='login')
def admin_drop_edit(request, drop_id):
    drop = get_object_or_404(ProjectDrop, id=drop_id)
    proyecto = drop.proyecto
    force_seller = request.GET.get('panel') == 'seller'
    
    is_admin, base_template = _get_panel_context(request, force_seller)
    is_owner = proyecto.owner == request.user
    
    if not is_admin and not is_owner:
        messages.error(request, "No tienes permiso para editar este drop.")
        return redirect('investor_dashboard')

    if request.method == 'POST':
        form = ProjectDropForm(request.POST, instance=drop, proyecto=proyecto)
        if form.is_valid():
            drop = form.save(commit=False)
            
            porcentaje = form.cleaned_data['porcentaje_tokens']
            drop.tokens_disponibles_drop = round(proyecto.tokens_totales * porcentaje / 100)
            
            drop.save()
            messages.success(request, "Drop actualizado exitosamente.")
            redirect_url = f"/admin-panel/drops/project/{proyecto.id}/"
            if force_seller:
                redirect_url += "?panel=seller"
            return redirect(redirect_url)
    else:
        form = ProjectDropForm(instance=drop, proyecto=proyecto)

    return render(request, 'booking/admin/drop_form.html', {
        'form': form,
        'proyecto': proyecto,
        'drop': drop,
        'action': 'Editar',
        'base_template': base_template,
        'is_seller_panel': force_seller,
        'active_tab': 'drops',
    })

@login_required(login_url='login')
def admin_drop_delete(request, drop_id):
    drop = get_object_or_404(ProjectDrop, id=drop_id)
    proyecto = drop.proyecto
    force_seller = request.GET.get('panel') == 'seller'
    
    is_admin, base_template = _get_panel_context(request, force_seller)
    is_owner = proyecto.owner == request.user
    
    if not is_admin and not is_owner:
        messages.error(request, "No tienes permiso para eliminar este drop.")
        return redirect('investor_dashboard')
        
    if request.method == 'POST':
        drop.delete()
        messages.success(request, "Drop eliminado.")
        redirect_url = f"/admin-panel/drops/project/{proyecto.id}/"
        if force_seller:
            redirect_url += "?panel=seller"
        return redirect(redirect_url)
        
    return redirect('admin_project_drops', project_id=proyecto.id)
